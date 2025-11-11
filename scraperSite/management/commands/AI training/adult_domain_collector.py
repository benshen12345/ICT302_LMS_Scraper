import os
import csv
import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Fetch all adult URLs from Bon-Appetit sources and save clean domains to CSV"

    def handle(self, *args, **options):
        bl_sources_url = "https://raw.githubusercontent.com/Bon-Appetit/porn-domains/main/blacklist/bl-sources.txt"
        output_dir = "datasets/train"
        output_csv = os.path.join(output_dir, "adult_domains.csv")
        all_urls = set()  # deduplicate

        self.stdout.write(f"Fetching source list from {bl_sources_url}")
        try:
            response = requests.get(bl_sources_url, timeout=15)
            response.raise_for_status()
            # Filter out empty lines and comment lines
            source_urls = [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith(("#", "!"))]
        except Exception as e:
            self.stderr.write(f"Failed to fetch bl-sources.txt: {e}")
            return

        self.stdout.write(f"Found {len(source_urls)} source URLs. Fetching content from each...")

        for url in source_urls:
            self.stdout.write(f"Fetching {url}")
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                for line in r.text.splitlines():
                    line = line.strip().lower()
                    # Skip empty lines and comments
                    if not line or line.startswith(("#", "!")):
                        continue

                    # Remove quotes and trailing commas
                    line = line.strip('"').strip("'").rstrip(",")

                    # Remove 'cname' word if present
                    if "cname" in line:
                        line = line.replace("cname", "").strip()

                    # Handle $websocket,domain=... lines
                    if line.startswith("$") and "domain=" in line:
                        domains_part = line.split("domain=")[1]
                        for d in domains_part.split("|"):
                            d = d.strip()
                            # Remove leading *.
                            if d.startswith("*."):
                                d = d[2:]
                            # Remove trailing dot
                            d = d.rstrip(".")
                            if d:
                                all_urls.add(d)
                        continue

                    # Split multiple domains separated by |
                    for d in line.split("|"):
                        d = d.strip()
                        # Remove leading *.
                        if d.startswith("*."):
                            d = d[2:]
                        # Remove trailing dot
                        d = d.rstrip(".")
                        if d:
                            all_urls.add(d)

            except Exception as e:
                self.stderr.write(f"Failed to fetch {url}: {e}")
                continue

        self.stdout.write(f"Writing {len(all_urls)} unique domains to {output_csv}")
        try:
            with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for url in sorted(all_urls):
                    writer.writerow([url])
        except Exception as e:
            self.stderr.write(f"Failed to write CSV: {e}")
            return

        self.stdout.write(self.style.SUCCESS(f"Successfully saved {len(all_urls)} domains to {output_csv}"))
