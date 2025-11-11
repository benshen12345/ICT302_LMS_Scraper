from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import User
from .user_log_event import user_log_event  # must exist in same folder

@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    if isinstance(user, User):
        user_log_event("LOGIN", user)

@receiver(user_logged_out)
def on_user_logout(sender, request, user, **kwargs):
    if isinstance(user, User):
        user_log_event("LOGOUT", user)
