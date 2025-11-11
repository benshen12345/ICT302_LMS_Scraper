from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import (
    MoodleCourse, User,
    MoodleContext, MoodleRoleAssign,
    MoodleUser, MoodleRole, ScanReport
)
from django.urls import reverse
from datetime import datetime, timedelta
from pathlib import Path
from django.contrib import messages
import json
from django.core.management import call_command
from django.utils import timezone

from .user_log_event import user_log_event
from .manual_scan_activity import append_activity_log


# -----------------------------
# Login / Logout
# -----------------------------
def login_view(request):
    message = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                request.session['username'] = user.username
                user_log_event("LOGIN", user)
                append_activity_log("LOGIN", user.username)
                return redirect('home')
            else:
                message = "Incorrect password"
        except User.DoesNotExist:
            message = "User does not exist"

    return render(request, 'scraperSite/login.html', {'message': message})


def logout_view(request):
    username = request.session.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
            user_log_event("LOGOUT", user)
            append_activity_log("LOGOUT", user.username)
        except User.DoesNotExist:
            pass
    request.session.flush()
    return redirect('login')


# -----------------------------
# Home Page (Dashboard)
# -----------------------------
def home(request):
    username = request.session.get('username')
    if not username:
        return redirect(reverse('login'))

    user = User.objects.get(username=username)
    fullname = user.fullname

    base_dir = Path("url_details")
    all_dates = []
    if base_dir.exists():
        for folder in base_dir.iterdir():
            if folder.is_dir():
                try:
                    d = datetime.strptime(folder.name, "%Y-%m-%d")
                    all_dates.append(d)
                except ValueError:
                    continue

    years = sorted({d.year for d in all_dates}, reverse=True)
    year_month_map = {}
    month_period_map = {}

    for year in years:
        months_for_year = sorted({d.month for d in all_dates if d.year == year})
        year_month_map[year] = months_for_year
        for month in months_for_year:
            month_dates = [d for d in all_dates if d.year == year and d.month == month]
            weeks = {}
            for d in month_dates:
                monday = d - timedelta(days=d.weekday())
                sunday = monday + timedelta(days=6)
                key = monday.strftime("%Y-%m-%d")
                label = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b')}"
                weeks[key] = label
            month_period_map[f"{year}-{month}"] = weeks

    latest_date = max(all_dates) if all_dates else datetime.now()
    selected_year = latest_date.year
    selected_month = latest_date.month
    latest_monday = latest_date - timedelta(days=latest_date.weekday())
    selected_period_key = latest_monday.strftime("%Y-%m-%d")

    context = {
        'fullname': fullname,
        'years': years,
        'year_month_map': year_month_map,
        'month_period_map_json': json.dumps(month_period_map),
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_period_key': selected_period_key,
    }

    return render(request, 'scraperSite/home.html', context)


# -----------------------------
# Helper: Courses + Managers
# -----------------------------
def build_courses_and_managers():
    courses_qs = MoodleCourse.objects.using("moodle").all()
    managers = {}

    for c in courses_qs:
        context_ids = MoodleContext.objects.using("moodle").filter(
            contextlevel=50, instanceid=c.id
        ).values_list('id', flat=True)

        manager_role_ids = MoodleRole.objects.using("moodle").filter(
            shortname='editingteacher'
        ).values_list('id', flat=True)

        manager_user_ids = MoodleRoleAssign.objects.using("moodle").filter(
            roleid__in=manager_role_ids,
            contextid__in=context_ids
        ).values_list('userid', flat=True)

        users = MoodleUser.objects.using("moodle").filter(id__in=manager_user_ids)
        managers[c.id] = [
            {"name": f"{u.firstname} {u.lastname}", "email": u.email}
            for u in users
        ]

    return courses_qs, managers


# -----------------------------
# Manual Scan Page
# -----------------------------
def manual_scan(request):
    username = request.session.get('username')
    if not username:
        return redirect(reverse('login'))

    user = User.objects.get(username=username)
    fullname = user.fullname

    if request.method == "POST":
        course_id = request.POST.get("course_id")
        if not course_id:
            messages.warning(request, "Please select a course to scan.")
            return redirect(request.path)

        try:
            course = MoodleCourse.objects.using("moodle").get(id=course_id)
        except MoodleCourse.DoesNotExist:
            messages.error(request, "Selected course does not exist.")
            return redirect(request.path)

        # ✅ Run scan as manual type
        call_command("URL_collector_single", course_id=course_id, scan_type="manual")

        append_activity_log("SCAN", username, course.fullname)

        reports = ScanReport.objects.filter(moodle_courseID=course_id).order_by('-report_id')
        if reports.exists():
            latest = reports.first()
            all_logs = (
                f"--- Report {latest.report_id} ({latest.date}) ---\n"
                f"Total Links: {latest.total_link}\n"
                f"Safe Links: {latest.safe_link}\n"
                f"Suspicious: {latest.suspicious}, Malicious: {latest.malicious}\n"
                "Unsafe URLs:\n"
            )
            unsafe_urls = latest.unsafe_urls.all()
            if unsafe_urls.exists():
                for url in unsafe_urls:
                    all_logs += f"- [Label: {url.status}, Source: {url.source}] {url.url}\n"
            else:
                all_logs += "None\n"
        else:
            all_logs = "No scan reports found for this course."

        courses, course_managers = build_courses_and_managers()
        course_managers_json = json.dumps(course_managers)

        return render(request, "scraperSite/manual_scan.html", {
            "courses": courses,
            "fullname": fullname,
            "course_managers_json": course_managers_json,
            "scan_result": all_logs,
            "course_name": course.fullname,
        })

    courses, course_managers = build_courses_and_managers()
    course_managers_json = json.dumps(course_managers)
    return render(request, "scraperSite/manual_scan.html", {
        "courses": courses,
        "fullname": fullname,
        "course_managers_json": course_managers_json,
    })


# -----------------------------
# Guide Page
# -----------------------------
def guide(request):
    username = request.session.get('username')
    fullname = User.objects.get(username=username).fullname if username else "Guest"
    return render(request, 'scraperSite/guide.html', {'fullname': fullname})


# -----------------------------
# Period Log View (Automatic Weekly Logs)
# -----------------------------
def view_scanned_log(request):
    username = request.session.get('username')
    if not username:
        return redirect('login')

    period_key = request.POST.get("period")
    if not period_key:
        return HttpResponse("No period selected.")

    monday_date = datetime.strptime(period_key, "%Y-%m-%d")
    sunday_date = monday_date + timedelta(days=6)

    base_dir = Path("url_details")
    all_files_content = ""

    if base_dir.exists():
        for folder in base_dir.iterdir():
            if folder.is_dir():
                try:
                    folder_date = datetime.strptime(folder.name, "%Y-%m-%d")
                except ValueError:
                    continue

                if monday_date <= folder_date <= sunday_date:
                    # 🔥 AUTO ONLY
                    for txt_file in folder.glob("auto_*_scanned.txt"):
                        all_files_content += f"\n--- {txt_file.name} ---\n"
                        all_files_content += txt_file.read_text(encoding="utf-8") + "\n"

    if not all_files_content:
        all_files_content = "No logs found for this period."

    return render(request, 'scraperSite/scanned_logs.html', {
        'fullname': User.objects.get(username=username).fullname,
        'log_content': all_files_content,
        'label': f"{monday_date.strftime('%d %b')} - {sunday_date.strftime('%d %b')}"
    })

# -----------------------------
# Manual Scan Log Page (per course)
# -----------------------------
def manual_scan_log(request):
    username = request.session.get('username')
    if not username:
        return redirect('login')

    user = User.objects.get(username=username)

    course_id = request.GET.get('course_id')
    if not course_id:
        messages.error(request, "No course selected for log view.")
        return redirect('manual_scan')

    try:
        course = MoodleCourse.objects.using("moodle").get(id=course_id)
    except MoodleCourse.DoesNotExist:
        messages.error(request, "Selected course does not exist.")
        return redirect('manual_scan')

    course_name = course.fullname

    base_dir = Path("url_details")
    all_files_content = ""

    if base_dir.exists():
        for folder in base_dir.iterdir():
            if not folder.is_dir():
                continue

            # 🔥 MANUAL ONLY
            for txt_file in folder.glob("manual_*_scanned.txt"):
                try:
                    txt = txt_file.read_text(encoding="utf-8")
                except Exception:
                    continue

                if f"Course Name: {course_name}" not in txt:
                    continue

                all_files_content += f"\n--- {txt_file.name} ---\n"
                all_files_content += txt + "\n"

    if not all_files_content:
        all_files_content = "No logs found for this course."

    return render(request, "scraperSite/manual_scan_log.html", {
        "fullname": user.fullname,
        "course_name": course_name,
        "log_content": all_files_content,
    })

