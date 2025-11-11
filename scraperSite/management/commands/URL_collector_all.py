from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from scraperSite.models import MoodleCourse
from scraperSite.management.helpers.URL_collector_helper import export_course_urls
from datetime import timedelta

class Command(BaseCommand):
    help = "Export and immediately scan Moodle URLs for courses that are visible or starting soon"

    def handle(self, *args, **options):
        now_ts = int(timezone.now().timestamp())
        cutoff_ts = now_ts + 4 * 7 * 24 * 60 * 60  # 4 weeks ahead

        # Fetch courses
        courses = []
        for c in MoodleCourse.objects.using("moodle").all():
            start_ts = int(c.startdate)
            # If timestamp is in milliseconds, convert to seconds
            if start_ts > 1e12:
                start_ts = start_ts // 1000

            if c.visible == 1:
                courses.append(c)
            elif c.visible == 0 and now_ts <= start_ts <= cutoff_ts:
                courses.append(c)

        if not courses:
            self.stdout.write(self.style.WARNING("⚠️ No courses found matching criteria."))
            return

        total = 0
        for course in courses:
            scanner_file = export_course_urls(course)
            if not scanner_file:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ No URLs found for course: {course.fullname}"
                ))
                continue

            total += 1
            self.stdout.write(self.style.SUCCESS(
                f"✅ Prepared URLs for scanning: {scanner_file}"
            ))

            # 🧩 Run the scanner immediately for this file
            self.stdout.write(f"🔍 Scanning URLs for: {course.fullname} ...")
            try:
                call_command("URL_scanner", file=scanner_file)
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Scan completed for: {course.fullname}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"❌ Error scanning {course.fullname}: {e}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"🎉 Completed URL export and scan for {total} course(s)."
        ))
