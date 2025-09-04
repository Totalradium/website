from django.urls import path, include
from bri import views
from bri.whatsapp_views import send_test_message, automate_whatsapp_messages
from bri.test_views import test_whatsapp_page, test_whatsapp_send
from django.shortcuts import redirect

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),  # Admin dashboard
    path('support/', views.support, name='support'),  # Support page
    path('add_user/', views.add_user, name='add_user'),  # Add new user
    path('logout/', views.logout_view, name='logout'),  # Logout
    path('student/', views.studentss, name='studentss'),  # Add student
    path('list_students/', views.list_students, name='list_students'),  # List of students
    path('batch/', views.batch_management, name='batch_management'),  # Manage batches
    path('edit-batch/<int:batch_id>/', views.edit_batch, name='edit_batch'),  # Edit batch
    path('disable_batch/', views.disable_batch, name='disable_batch'),  # Disable batch
    path('update_section/<int:sec_id>/', views.update_section, name='update_section'),  # Add this line for updating sections
    path('delete_section/<int:sec_id>/', views.delete_section, name='delete_section'),
    path('get_sections_for_class/<int:class_id>/', views.get_sections_for_class, name='get_sections_for_class'),
    path('get_students_for_section/<int:class_id>/<int:section_id>/', views.get_students_for_section, name='get_students_for_section'),
    path('create_user/', views.create_user, name='create_user'),
    path('disable_section/<int:sec_id>/', views.disable_section, name='disable_section'),
    path('promote_batch/',views.promote_batch, name='promote_batch'),
    path('students/<int:student_id>/edit/', views.edit_students, name='edit_students'),
    path('students/manage/', views.delete_disable_students, name='delete_disable_students'),
    path('students/promote/', views.promote_students, name='promote_students'),
    path('attendance_dashboard/', views.attendance_dashboard, name='attendance_dashboard'),
    path('attendance/', views.attendance_home, name='attendance_home'),
    path('attendance/load/', views.attendance_view, name='attendance_view'),
    path('attendance/save/', views.save_attendance, name='save_attendance'),
    path('attendance/monthly_report/', views.student_monthly_report, name='student_monthly_report'),
    path('attendance/export/', views.export_attendance, name='export_attendance'),
    path('whatsapp/', views.whatsapp_integration, name='whatsapp_integration'),
    path('get_students_with_attendance/', views.get_students_with_attendance, name='get_students_with_attendance'),
    path('get_students_with_fees/', views.get_students_with_fees, name='get_students_with_fees'),
    path('automate_whatsapp/', automate_whatsapp_messages, name='automate_whatsapp_messages'),
    path('send_test_message/', send_test_message, name='send_test_message'),
    path('test_whatsapp/', test_whatsapp_page, name='test_whatsapp_page'),
    path('test_whatsapp_send/', test_whatsapp_send, name='test_whatsapp_send'),
    path('teacher_attendance/', views.teacher_attendance, name='teacher_attendance'),
    path('teacher_attendance_report/', views.teacher_attendance_report, name='teacher_attendance_report'),
    path('add_teacher/', views.add_teacher, name='add_teacher'),
    path('edit_teacher/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('delete_teacher/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    path('fee_dashboard/', views.fee_dashboard, name='fee_dashboard'),
    path('fee_management/', views.fee_management, name='fee_management'),
    path('submit_fee/<int:fee_id>/', views.submit_fee, name='submit_fee'),
    path('fee_reports/', views.fee_reports, name='fee_reports'),
    path('defaulter_list/', views.defaulter_list, name='defaulter_list'),
    path('bulk_fee_collection/', views.bulk_fee_collection, name='bulk_fee_collection'),
    path('edit_fee/<int:fee_id>/', views.edit_fee, name='edit_fee'),
    path('delete_fee/<int:fee_id>/', views.delete_fee, name='delete_fee'),
    path('barcode_fee_entry/', views.barcode_fee_entry, name='barcode_fee_entry'),
    path('voucher_generator/', views.voucher_generator, name='voucher_generator'),
    path('print_single_voucher/<int:student_id>/', views.print_single_voucher, name='print_single_voucher'),
    path('print_vouchers/', views.print_vouchers, name='print_vouchers'),
    path('mark_fee_paid/<int:student_fee_id>/', views.mark_fee_paid, name='mark_fee_paid'),
    path('edit_user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('logout/', views.logout_view, name='logout_view'),
    path('attendance_notifications/', views.attendance_notification_log, name='attendance_notifications'),
    path('send_notification/', views.send_notification, name='send_notification'),
    path('send_all_notifications/', views.send_all_notifications, name='send_all_notifications'),
    path('get_pending_count/', views.get_pending_count, name='get_pending_count'),
    path('get_message_templates/', views.get_message_templates, name='get_message_templates'),
    path('create_message_template/', views.create_message_template, name='create_message_template'),
    path('edit_message_template/<int:template_id>/', views.edit_message_template, name='edit_message_template'),
    path('message_templates/', views.message_templates, name='message_templates'),
    path('fee_logs/', views.fee_logs, name='fee_logs'),
    path('test_management/', views.test_management, name='test_management'),
    path('create_test_session/', views.create_test_session, name='create_test_session'),
    path('session_detail/<int:session_id>/', views.session_detail, name='session_detail'),
    path('enter_marks/<int:test_id>/', views.enter_marks, name='enter_marks'),
    path('print_result_cards/<int:session_id>/', views.print_result_cards, name='print_result_cards'),
    path('get_subjects_for_session/<int:class_id>/<int:section_id>/', views.get_subjects_for_session, name='get_subjects_for_session'),
    path('subject_management/', views.subject_management, name='subject_management'),
    path('delete_subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('update_subject/<int:subject_id>/', views.update_subject, name='update_subject'),
    path('move_class/<int:class_id>/<str:direction>/', views.move_class, name='move_class'),
    path('toggle_teacher/<int:teacher_id>/', views.toggle_teacher, name='toggle_teacher'),
    path('edit_test_session/<int:session_id>/', views.edit_test_session, name='edit_test_session'),
    path('delete_test_session/<int:session_id>/', views.delete_test_session, name='delete_test_session'),
    path('delete_test/<int:test_id>/', views.delete_test, name='delete_test'),
    path('select_tests_for_print/<int:session_id>/', views.select_tests_for_print, name='select_tests_for_print'),
    path('get_message_status/', views.get_message_status, name='get_message_status'),
    
    # Timetable URLs
    path('timetable_management/', views.timetable_management, name='timetable_management'),
    path('view_timetable/', views.view_timetable, name='view_timetable'),
    path('edit_timetable_entry/<int:entry_id>/', views.edit_timetable_entry, name='edit_timetable_entry'),
    path('delete_timetable_entry/<int:entry_id>/', views.delete_timetable_entry, name='delete_timetable_entry'),
    
    # Reports URLs
    path('', include('bri.reports_urls')),
]
