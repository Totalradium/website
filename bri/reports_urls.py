from django.urls import path
from . import reports_views

urlpatterns = [
    path('reports/', reports_views.reports_dashboard, name='reports_dashboard'),
    path('reports/students/', reports_views.student_reports, name='student_reports'),
    path('reports/exams/', reports_views.exam_reports, name='exam_reports'),
    path('reports/fees/', reports_views.fee_reports_export, name='fee_reports_export'),
    path('reports/users/', reports_views.user_reports, name='user_reports'),
    path('reports/logs/', reports_views.activity_logs, name='activity_logs'),
]