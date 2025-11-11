from pathlib import Path
from django.utils import timezone

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "manual_scan_activity.log"


def append_activity_log(action: str, username: str, course_name: str | None = None):
    """
    Write one line only for SCAN actions:
      YYYY-mm-dd HH:MM:SS | SCAN | username | course_name
    Ignores LOGIN and LOGOUT actions.
    """
    if action != "SCAN":
        return  # skip non-scan actions

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    course_part = course_name if course_name else "-"
    line = f"{ts} | {action} | {username} | {course_part}\n"

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
