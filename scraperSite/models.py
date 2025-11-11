from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import datetime

# --------------------------
# Internal Users & Reports
# --------------------------

class User(models.Model):
    userid = models.AutoField(primary_key=True)
    username = models.CharField(max_length=15)
    fullname = models.CharField(max_length=50)
    password = models.CharField(max_length=128)
    email = models.CharField(max_length=50)
    last_login = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.fullname

    class Meta:
        managed = True
        app_label = 'scraperSite'


class ScanReport(models.Model):
    report_id = models.AutoField(primary_key=True)
    date = models.DateField()
    total_link = models.IntegerField()
    safe_link = models.IntegerField()
    suspicious = models.IntegerField()
    malicious = models.IntegerField()
    moodle_courseID = models.IntegerField()
    moodle_courseName = models.CharField(max_length=200)
    all_url = models.CharField(max_length=100)

    def __str__(self):
        return f"Report {self.report_id}"

    class Meta:
        managed = True
        app_label = 'scraperSite'


class UnsafeURL(models.Model):
    STATUS_CHOICES = (
        ('malware', 'Malware'),
        ('phish', 'Phish'),
        ('adult', 'Adult'),
        ('suspicious', 'Suspicious'),
    )
    CHECK_STATUS_CHOICES = (
        ('safe', 'Safe'),
        ('not safe', 'Not Safe'),
    )

    url_id = models.AutoField(primary_key=True)
    url = models.CharField(max_length=350)
    moodle_userID = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    check_status = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default='not safe')
    source = models.CharField(max_length=50)
    report = models.ForeignKey(ScanReport, on_delete=models.CASCADE, related_name='unsafe_urls')

    def __str__(self):
        return self.status

    class Meta:
        managed = True
        app_label = 'scraperSite'


# --------------------------
# Moodle Tables
# --------------------------

class MoodleCourse(models.Model):
    id = models.IntegerField(primary_key=True)
    fullname = models.CharField(max_length=255)
    # ✅ Map Moodle's timecreated column (UNIX timestamp)
    timecreated = models.BigIntegerField()
    startdate = models.BigIntegerField()
    visible = models.IntegerField()  # 1 = visible, 0 = hidden

    @property
    def created_dt(self):
        """
        Convert Moodle's UNIX timestamp (seconds since epoch)
        into a timezone-aware datetime in Django.
        """
        if not self.timecreated:
            return None
        try:
            return datetime.fromtimestamp(int(self.timecreated), timezone.get_current_timezone())
        except (TypeError, ValueError, OSError):
            return None

    @property
    def start_dt(self):
        try:
            return datetime.fromtimestamp(int(self.startdate), timezone.get_current_timezone())
        except:
            return None


    class Meta:
        managed = False
        db_table = 'mdl_course'
        app_label = 'scraperSite'


class MoodleChat(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.IntegerField()
    name = models.CharField(max_length=255)
    intro = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'mdl_chat'
        app_label = 'scraperSite'


class MoodleChatMessage(models.Model):
    id = models.AutoField(primary_key=True)
    chatid = models.IntegerField()
    userid = models.IntegerField(null=True)
    message = models.TextField()

    class Meta:
        managed = False
        db_table = 'mdl_chat_messages'
        app_label = 'scraperSite'


class MoodleUrl(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(MoodleCourse, on_delete=models.DO_NOTHING, db_column='course')
    name = models.CharField(max_length=255)
    externalurl = models.TextField()

    class Meta:
        managed = False
        db_table = 'mdl_url'
        app_label = 'scraperSite'


class MoodleModules(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'mdl_modules'
        app_label = 'scraperSite'


class MoodleCourseModules(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.IntegerField()
    module = models.IntegerField()
    instance = models.IntegerField()
    section = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'mdl_course_modules'
        app_label = 'scraperSite'


class MoodleCourseSection(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.IntegerField()
    section = models.IntegerField()
    name = models.CharField(max_length=255, null=True)

    class Meta:
        managed = False
        db_table = 'mdl_course_sections'
        app_label = 'scraperSite'


class MoodleUser(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.CharField(max_length=100)

    @property
    def fullname(self):
        return f"{self.firstname} {self.lastname}"

    class Meta:
        managed = False
        db_table = 'mdl_user'
        app_label = 'scraperSite'


class MoodleRoleAssign(models.Model):
    id = models.AutoField(primary_key=True)
    userid = models.IntegerField()
    contextid = models.IntegerField()
    roleid = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'mdl_role_assignments'
        app_label = 'scraperSite'


class MoodleContext(models.Model):
    id = models.AutoField(primary_key=True)
    contextlevel = models.IntegerField()
    instanceid = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'mdl_context'
        app_label = 'scraperSite'


class MoodleRole(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    shortname = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'mdl_role'
        app_label = 'scraperSite'


# --------------------------
# Moodle Forum Tables (Moodle 4+)
# --------------------------

class Forum(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.IntegerField()
    name = models.CharField(max_length=255)
    intro = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=20)  # standard, qanda, single, etc.

    class Meta:
        managed = False
        db_table = 'mdl_forum'
        app_label = 'scraperSite'


class ForumDiscussion(models.Model):
    id = models.AutoField(primary_key=True)
    forum = models.IntegerField()
    name = models.CharField(max_length=255)  # discussion title
    userid = models.IntegerField(null=True)  # author

    class Meta:
        managed = False
        db_table = 'mdl_forum_discussions'
        app_label = 'scraperSite'


class ForumPost(models.Model):
    id = models.AutoField(primary_key=True)
    discussion = models.IntegerField()
    userid = models.IntegerField(null=True)  # author
    message = models.TextField()  # actual post content

    class Meta:
        managed = False
        db_table = 'mdl_forum_posts'
        app_label = 'scraperSite'
