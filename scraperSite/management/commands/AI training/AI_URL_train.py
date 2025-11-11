# app/management/commands/train_url_model.py
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os, re, joblib, tldextract
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

class Command(BaseCommand):
    help = "Train URL classification model (benign, phish, malware, adult)"

    def handle(self, *args, **options):
        try:
            self.stdout.write("📂 Loading dataset...")
            dataset_path = Path(settings.BASE_DIR) / "datasets/train/merged_urls_dataset.csv"
            if not dataset_path.exists():
                self.stderr.write(f"❌ Dataset not found: {dataset_path}")
                return

            df_all = pd.read_csv(dataset_path)

            # ------------------------
            # Feature extraction
            # ------------------------
            self.stdout.write("🔧 Extracting lexical features...")

            def entropy(s):
                if not s: return 0.0
                probs = np.array([s.count(c) for c in set(s)], dtype=float)
                probs /= probs.sum()
                return -(probs * np.log2(probs)).sum()

            def url_lexical_features(df):
                out = pd.DataFrame()
                out['url_len'] = df['url'].apply(len)
                out['num_dots'] = df['url'].apply(lambda u: u.count('.'))
                out['num_digits'] = df['url'].apply(lambda u: sum(c.isdigit() for c in u))
                out['path_len'] = df['url'].apply(lambda u: len(re.sub(r'^https?://[^/]+', '', u)))
                out['char_entropy'] = df['url'].apply(entropy)
                return out

            num_feats = url_lexical_features(df_all)
            df_all = pd.concat([df_all, num_feats], axis=1)

            # Extract textual feature
            df_all['url_text'] = df_all['url'].apply(
                lambda u: tldextract.extract(u).registered_domain + " " + re.sub(r'https?://[^/]+', '', u)
            )

            # Map labels
            mapping = {"benign":0, "phish":1, "malware":2, "adult":3}
            y = df_all['label'].map(mapping)

            text_cols = 'url_text'
            numeric_cols = ['url_len', 'num_dots', 'num_digits', 'path_len', 'char_entropy']

            text_transformer = Pipeline([
                ('tfidf', TfidfVectorizer(ngram_range=(1,3), analyzer='char_wb', max_features=2000))
            ])
            num_transformer = Pipeline([
                ('scaler', StandardScaler())
            ])
            preprocessor = ColumnTransformer([
                ('text', text_transformer, text_cols),
                ('num', num_transformer, numeric_cols)
            ])

            clf = Pipeline([
                ('pre', preprocessor),
                ('clf', RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42))
            ])

            # ------------------------
            # Train/test split
            # ------------------------
            X = df_all[[text_cols] + numeric_cols]
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, stratify=y, random_state=42
            )

            self.stdout.write("🚀 Training model...")
            clf.fit(X_train, y_train)

            # ------------------------
            # Evaluation
            # ------------------------
            y_pred = clf.predict(X_test)
            y_proba = clf.predict_proba(X_test) if hasattr(clf, "predict_proba") else None

            report_str = classification_report(y_test, y_pred, target_names=["benign","phish","malware","adult"])
            self.stdout.write("\n📊 Classification Report:")
            self.stdout.write(report_str)

            if y_proba is not None:
                try:
                    auc = roc_auc_score(pd.get_dummies(y_test), y_proba, average='macro')
                    self.stdout.write(f"ROC-AUC (macro): {auc:.4f}")
                except Exception:
                    pass

            # ------------------------
            # Save model and report with timestamp
            # ------------------------
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_dir = Path(settings.BASE_DIR) / "trained_models"
            os.makedirs(model_dir, exist_ok=True)

            model_path = model_dir / f"url_classifier.pkl"
            joblib.dump(clf, model_path)
            self.stdout.write(self.style.SUCCESS(f"✅ Model saved to {model_path}"))

            report_path = model_dir / f"url_classifier_report.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("Classification Report\n")
                f.write("====================\n")
                f.write(report_str)
                if y_proba is not None:
                    try:
                        f.write(f"\nROC-AUC (macro): {auc:.4f}\n")
                    except:
                        pass
            self.stdout.write(self.style.SUCCESS(f"📄 Report saved to {report_path}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Training failed: {e}"))
