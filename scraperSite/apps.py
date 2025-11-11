from django.apps import AppConfig
import threading
import time
from django.core.management import call_command
import schedule
import os


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraperSite'

    def ready(self):
        if os.environ.get("RUN_MAIN")=="true":
            threading.Thread(target=self.run_scheduler, daemon=True).start()
        # Import login/logout signal handlers
        import scraperSite.signals

    def run_scheduler(self):
        # Schedule for every saturday at 01:00 AM
        schedule.every().saturday.at("01:00").do(self.run_scan)

        while True:
            schedule.run_pending()
            time.sleep(60)

    def run_scan(self):
        try:
            print("🛠️ [Auto] Courses' URLs scraping and scanning...")
            call_command("URL_collector_all")
        except Exception as e:
            print(f"⚠️ Error running scanner: {e}")

