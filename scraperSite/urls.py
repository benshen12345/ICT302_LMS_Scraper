from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('view_scanned_log/', views.view_scanned_log, name='view_scanned_log'),
    path('manual', views.manual_scan, name='manual_scan'),  # manual scan page
    path('guide/', views.guide, name='guide'),
    path('manual_scan_log/', views.manual_scan_log, name='manual_scan_log'),
]
