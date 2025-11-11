from django.core.management.base import BaseCommand
from pathlib import Path
from scraperSite.management.helpers.URL_scanner_helper import scan_from_file
from django.utils import timezone

class Command(BaseCommand):
    help = "Scan all exported URL TXT files (or one specific file)"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, help="Path to a specific TXT file to scan")

    def handle(self, *args, **options):
        today_str = timezone.localtime(timezone.now()).strftime("%Y-%m-%d")
        today_dir = Path("url_details") / today_str
        file_arg = options.get("file")

        if file_arg:
            scan_from_file(file_arg)
        else:
            txt_files = list(today_dir.glob("*.txt"))
            if not txt_files:
                print("⚠️ No TXT files found for today.")
                return

            for f in txt_files:
                scan_from_file(f)

