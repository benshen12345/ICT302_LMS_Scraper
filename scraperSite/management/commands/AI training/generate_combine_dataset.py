
import pandas as pd
import requests

from io import StringIO
adult_domains_path = "datasets/train/adult_domains.csv"
safe_domains_path = "datasets/train/safe_domains.csv"

# ---------------------------
# 1. Fetch CSV feeds
# ---------------------------
def fetch_urlhaus():
    url = "https://urlhaus.abuse.ch/downloads/csv_recent/"
    r = requests.get(url)
    r.raise_for_status()
    # URLhaus CSV: no header, skip comment lines starting with #
    df = pd.read_csv(
        StringIO(r.text),
        comment='#',
        header=None,
        names=[
            "id", "dateadded", "url", "status", "dateverified",
            "threat", "tags", "urlhaus_link", "reporter"
        ],
        engine='python',
        on_bad_lines='skip'
    )
    df = df[['url']]
    df['label'] = 'malware'
    return df


def fetch_phishtank():
    url = "https://data.phishtank.com/data/online-valid.csv"
    r = requests.get(url)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df = df[['url']]
    df['label'] = 'phish'
    return df

def fetch_adult_list():
    try:
        df = pd.read_csv(adult_domains_path, names=['url'])
        df['label'] = 'adult'
    except FileNotFoundError:
        df = pd.DataFrame({'url': [], 'label': []})
    return df

def fetch_safe_list():
    try:
        df = pd.read_csv(safe_domains_path, names=['url'])
        df['label'] = 'benign'
    except FileNotFoundError:
        df = pd.DataFrame({'url': [], 'label': []})
    return df

# ---------------------------
# 2. Normalize URLs
# ---------------------------
def normalize_url(u):
    u = u.strip()
    if not u.startswith("http"):
        u = "http://" + u
    return u.lower()



# ---------------------------
# 4. Load and merge datasets
# ---------------------------
df_malware = fetch_urlhaus()
df_phish = fetch_phishtank()
df_adult = fetch_adult_list()
df_safe = fetch_safe_list()

df_all = pd.concat([df_malware, df_phish, df_adult, df_safe], ignore_index=True)
df_all['url'] = df_all['url'].apply(normalize_url)
df_all = df_all.drop_duplicates(subset=['url'])

# Save merged dataset
df_all.to_csv("merged_urls_dataset.csv", index=False)
print("Merged CSV saved: merged_urls_dataset.csv")
print("Label distribution:\n", df_all['label'].value_counts())
