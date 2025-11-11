import os
from django.utils import timezone
from django.conf import settings

# logs directory inside BASE_DIR
LOG_DIR = os.path.join(settings.BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "user_logs.log")

def user_log_event(event_type, user):
    """
    Log user login/logout events to a text file.
    """

    # ensure logs folder exists
    os.makedirs(LOG_DIR, exist_ok=True)

    timestamp = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {event_type}: {user.username} ({user.fullname})\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
