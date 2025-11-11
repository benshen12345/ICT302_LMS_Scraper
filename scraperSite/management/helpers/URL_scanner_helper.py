import os
import re
import time
import numpy as np
import pandas as pd
import tldextract
import joblib
import requests
from pathlib import Path
from django.utils import timezone
from scraperSite.models import ScanReport, UnsafeURL

VT_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY")
VT_BASE = "https://www.virustotal.com/api/v3"
HEADERS = {"x-apikey": VT_API_KEY}

# -----------------------------
# VirusTotal helpers
# -----------------------------
def vt_submit_url(url):
    resp = requests.post(f"{VT_BASE}/urls", headers=HEADERS, data={"url": url}, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]["id"]

def vt_get_analysis(analysis_id):
    resp = requests.get(f"{VT_BASE}/analyses/{analysis_id}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def poll_analysis(analysis_id, timeout=120, interval=4):
    start = time.time()
    while True:
        data = vt_get_analysis(analysis_id)
        status = data["data"]["attributes"]["status"]

        if status == "completed":
            stats = data["data"]["attributes"]["stats"]
            results = data["data"]["attributes"].get("results", {})

            malicious_count = sum(
                1 for r in results.values()
                if r.get("category") in ["malicious", "phishing", "suspicious", "malware"]
            )

            if malicious_count >= 1:
                return True
            return any(stats.get(k, 0) > 0 for k in ["malware", "phishing", "suspicious", "adult"])

        if time.time() - start > timeout:
            print("⚠️ VT polling timeout — treating as safe.")
            return False
        time.sleep(interval)


# -----------------------------
# Local AI model loader
# -----------------------------
def load_ai_model(model_path="trained_models/url_classifier.pkl"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    return joblib.load(model_path)


# -----------------------------
# URL feature extraction
# -----------------------------
def url_lexical_features(urls):
    df = pd.DataFrame({"url": urls})
    df["url_len"] = df["url"].apply(len)
    df["num_dots"] = df["url"].apply(lambda u: u.count("."))
    df["num_digits"] = df["url"].apply(lambda u: sum(c.isdigit() for c in u))
    df["path_len"] = df["url"].apply(lambda u: len(re.sub(r"^https?://[^/]+", "", u)))

    def entropy(s):
        if not s:
            return 0.0
        probs = np.array([s.count(c) for c in set(s)], dtype=float)
        probs /= probs.sum()
        return -(probs * np.log2(probs)).sum()

    df["char_entropy"] = df["url"].apply(entropy)
    df["url_text"] = df["url"].apply(
        lambda u: tldextract.extract(u).registered_domain + " " + re.sub(r"https?://[^/]+", "", u)
    )
    return df


# -----------------------------
# Scan one exported TXT file
# -----------------------------
def scan_from_file(url_file):
    if not os.path.exists(url_file):
        print(f"⚠️ File not found: {url_file}")
        return

    print(f"📂 Scanning file: {url_file}")

    clf = load_ai_model()
    label_map = {0: "benign", 1: "phish", 2: "malware", 3: "adult"}

    df_original = pd.read_csv(url_file, dtype=str, quotechar='"')

    required_cols = ["url", "authorUsername", "authorName", "authorEmail", "source"]
    for c in required_cols:
        if c not in df_original.columns:
            df_original[c] = ""

    course_id = int(df_original.iloc[0].get("courseID", 0))
    course_name = df_original.iloc[0].get("courseName", "Unknown Course")

    urls_list = df_original["url"].tolist()
    df_features = url_lexical_features(urls_list)

    preds = clf.predict(df_features[["url_text", "url_len", "num_dots", "num_digits", "path_len", "char_entropy"]])
    probs = clf.predict_proba(df_features[["url_text", "url_len", "num_dots", "num_digits", "path_len", "char_entropy"]])
    df_features["pred_label"] = [label_map[p] for p in preds]
    df_features["confidence"] = np.max(probs, axis=1).round(4)

    df_combined = pd.concat([df_original.reset_index(drop=True),
                             df_features[["pred_label", "confidence"]].reset_index(drop=True)], axis=1)

    df_combined["vt_result"] = "not_checked"
    df_combined["final_status"] = "benign"

    report = ScanReport.objects.create(
        date=timezone.now().date(),
        total_link=len(df_combined),
        safe_link=0,
        suspicious=0,
        malicious=0,
        moodle_courseID=course_id,
        moodle_courseName=course_name,
        all_url=str(url_file)
    )

    safe_links, suspicious_links, malicious_links = 0, 0, 0

    for idx, row in df_combined.iterrows():
        url = row["url"]
        pred_label = row["pred_label"]
        confidence = row["confidence"]
        moodle_url_id = int(row.get("moodle_url_id", 0))
        source = row.get("source", "Unknown")

        vt_malicious = False
        vt_checked = False
        if confidence < 0.8 and VT_API_KEY:
            try:
                analysis_id = vt_submit_url(url)
                vt_malicious = poll_analysis(analysis_id)
                vt_checked = True
            except Exception as e:
                print(f"⚠️ VT error for {url}: {e}")

        if pred_label in ["adult", "phish", "malware"]:
            if confidence >= 0.8 or vt_malicious:
                status = pred_label
                malicious_links += 1
            elif 0.7 <= confidence < 0.8:
                status = "suspicious"
                suspicious_links += 1
            else:
                status = "benign"
                safe_links += 1
        else:
            if not vt_malicious:
                status = "benign"
                safe_links += 1
            else:
                status = "suspicious"
                suspicious_links += 1

        df_combined.at[idx, "vt_result"] = "malicious" if vt_malicious else ("checked" if vt_checked else "not_checked")
        df_combined.at[idx, "final_status"] = status

        if status != "benign":
            UnsafeURL.objects.create(
                url=url,
                moodle_userID=moodle_url_id,
                status=status,
                source=source,
                report=report
            )

    report.safe_link = safe_links
    report.suspicious = suspicious_links
    report.malicious = malicious_links
    report.save()

    # -----------------------------
    # Output File (manual vs auto separation)
    # -----------------------------
    today_str = timezone.localtime(timezone.now()).strftime("%Y-%m-%d")
    now_datetime = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
    export_dir = Path("url_details") / today_str
    export_dir.mkdir(parents=True, exist_ok=True)

    # 👇 Detect manual or auto scan type from input filename
    input_stem = Path(url_file).stem.lower()
    if input_stem.startswith("manual_"):
        scan_type = "manual"
    else:
        scan_type = "auto"

    file_path = export_dir / f"{scan_type}_{course_id}_{now_datetime}_scanned.txt"
    print(f"🗂️ Detected scan type: {scan_type.upper()}")

    export_cols = [
        "url", "authorUsername", "authorName", "authorEmail", "source",
        "pred_label", "confidence", "vt_result", "final_status"
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Exported on: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Course ID: {course_id}\nCourse Name: {course_name}\n")
        f.write("=" * 100 + "\n")
        f.write(",".join(export_cols) + "\n")
        for _, row in df_combined.iterrows():
            f.write(",".join(str(row[c]) for c in export_cols) + "\n")

    print(f"✅ Course {course_id} scanned successfully → {file_path}")
    print(f"   → Safe: {safe_links} | Suspicious: {suspicious_links} | Malicious: {malicious_links}")

    try:
        os.remove(url_file)
        print(f"🗑️ Removed input file: {url_file}")
    except Exception as e:
        print(f"⚠️ Could not remove input file: {e}")

    return report
