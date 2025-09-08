from django.urls import path
from . import views
from .api_views import sync_students_api, sync_attendance_api, sync_fees_api, sync_teachers_api, sync_exams_api, health_check
from .student_views import student_login, student_logout, student_dashboard, student_attendance, student_fees, student_results, print_fee_voucher, print_result_card

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Redirect /student/ to student login
    path('student/', student_login, name='student_portal'),
    
    # API endpoints for sync
    path('api/sync/students/', sync_students_api, name='sync_students_api'),
    path('api/sync/attendance/', sync_attendance_api, name='sync_attendance_api'),
    path('api/sync/fees/', sync_fees_api, name='sync_fees_api'),
    path('api/sync/teachers/', sync_teachers_api, name='sync_teachers_api'),
    path('api/sync/exams/', sync_exams_api, name='sync_exams_api'),
    path('api/health/', health_check, name='health_check'),
    
    # Student Portal
    path('student/login/', student_login, name='student_login'),
    path('student/logout/', student_logout, name='student_logout'),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('student/attendance/', student_attendance, name='student_attendance'),
    path('student/fees/', student_fees, name='student_fees'),
    path('student/results/', student_results, name='student_results'),
    path('student/voucher/', print_fee_voucher, name='print_fee_voucher'),
    path('student/result-card/<int:session_id>/', print_result_card, name='print_result_card'),
    
    # View endpoints (read-only for online access)
    path('students/', views.students_list, name='students_list'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('fees/', views.fees_list, name='fees_list'),
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('exams/', views.exams_list, name='exams_list'),
]