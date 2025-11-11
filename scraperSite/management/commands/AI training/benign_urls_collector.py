import csv
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Filter benign URLs from malicious_phish.csv and save to safe_domains.csv"

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        input_path = "datasets/unprocessed_benign/malicious_phish.csv"
        output_dir = "datasets/train"
        output_csv = os.path.join(output_dir, "safe_domains.csv")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        benign_urls = []

        # Read and filter
        with open(input_path, "r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get("type") == "benign":
                    benign_urls.append(row["url"])

        # Write filtered URLs without header
        with open(output_csv, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            for url in benign_urls:
                writer.writerow([url])

        self.stdout.write(self.style.SUCCESS(f"✅ Saved {len(benign_urls)} benign URLs to {output_csv}"))
