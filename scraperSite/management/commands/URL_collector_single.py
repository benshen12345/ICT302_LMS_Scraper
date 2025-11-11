# scraperSite/management/commands/URL_collector_single.py

from django.core.management.base import BaseCommand
from scraperSite.models import MoodleCourse
from scraperSite.management.helpers.URL_collector_helper import export_course_urls
from scraperSite.management.helpers.URL_scanner_helper import scan_from_file


class Command(BaseCommand):
    help = "Collect URLs from a single Moodle course and run the AI/VT scanner."

    def add_arguments(self, parser):
        parser.add_argument(
            '--course_id',
            type=int,
            required=True,
            help='Course ID to scan',
        )
        parser.add_argument(
            '--scan_type',
            type=str,
            default='auto',
            choices=['auto', 'manual'],
            help='Specify scan type: auto or manual',
        )

    def handle(self, *args, **options):
        course_id = options['course_id']
        scan_type = options.get('scan_type', 'auto')

        self.stdout.write(
            f"🔍 Starting URL Collector for course_id={course_id} [{scan_type.upper()}]"
        )

        # 1️⃣ Get course
        try:
            course = MoodleCourse.objects.using("moodle").get(id=course_id)
        except MoodleCourse.DoesNotExist:
            self.stderr.write(f"❌ Course ID {course_id} not found in Moodle DB.")
            return

        # 2️⃣ Export URLs
        try:
            url_file = export_course_urls(course, scan_type=scan_type)
            self.stdout.write(f"📄 Exported URLs → {url_file}")
        except Exception as e:
            self.stderr.write(f"⚠️ Failed to export URLs: {e}")
            return

        # 3️⃣ Run scanning
        try:
            report = scan_from_file(url_file)
            self.stdout.write(f"✅ Scan complete → Report #{report.report_id}")
        except Exception as e:
            self.stderr.write(f"❌ Scan failed: {e}")
