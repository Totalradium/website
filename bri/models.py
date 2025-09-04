from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from datetime import date, timedelta
from calendar import monthrange
from django import forms
from django.contrib.auth.hashers import make_password
import os
import uuid
from django.core.files import File
from io import BytesIO
from django.shortcuts import get_object_or_404,redirect
from barcode import get_barcode_class
from django.contrib import messages
from barcode.writer import ImageWriter

# -----------------------
# CLASS & SECTION
# -----------------------
class Class(models.Model):
    class_name = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.class_name
    
    class Meta:
        ordering = ['order', 'class_name']

class Section(models.Model):
    std_section = models.CharField(max_length=10)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="sections")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.std_section
    
    class Meta:
        ordering = ['order', 'std_section']

# -----------------------
# USERNAME / LOGIN
# -----------------------
class Username(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk is None and self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super(Username, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

# -----------------------
# STUDENT
# -----------------------
class Student(models.Model):
    username = models.OneToOneField(Username, on_delete=models.CASCADE, related_name='student_profile')
    std_fname = models.CharField(max_length=20)
    std_lname = models.CharField(max_length=20)
    std_dob = models.DateField()
    std_roll = models.SmallIntegerField()
    std_class = models.ForeignKey(Class, on_delete=models.CASCADE)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_contact1 = PhoneNumberField(blank=True, null=True)
    guardian_contact2 = PhoneNumberField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    std_section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    gender = models.CharField(max_length=10)
    discount_amount = models.IntegerField(help_text="Discount amount in PKR")
    is_active = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='student_pics/', blank=True, null=True)

    class Meta:
        unique_together = ('std_class', 'std_roll')

    def __str__(self):
        return f"{self.std_fname} {self.std_lname}"

# -----------------------
# TEACHER
# -----------------------
class Teacher(models.Model):
    username = models.OneToOneField(Username, on_delete=models.CASCADE, related_name="teacher_profile")
    teacher_fname = models.CharField(max_length=20)
    teacher_lname = models.CharField(max_length=20)
    phone1 = PhoneNumberField()
    phone2 = PhoneNumberField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='teacher_pics/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.teacher_fname} {self.teacher_lname}"

# -----------------------
# SUBJECTS PER CLASS+SECTION
# -----------------------
class SectionSubject(models.Model):
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="section_subjects")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="section_subjects")
    subject = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    academic_year = models.CharField(max_length=9)

    class Meta:
        unique_together = ('class_name', 'section', 'subject', 'academic_year')
        indexes = [
            models.Index(fields=['class_name', 'section', 'subject']),
        ]

    def __str__(self):
        return f"{self.class_name.class_name}-{self.section.std_section} · {self.subject} · {self.academic_year}"

# -----------------------
# TEACHER ↔ SUBJECT
# -----------------------
class TeacherSubjectAssignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
    section_subject = models.ForeignKey(SectionSubject, on_delete=models.CASCADE, related_name="assignments")

    class Meta:
        unique_together = ('teacher', 'section_subject')

    def __str__(self):
        ss = self.section_subject
        return f"{self.teacher} -> {ss.subject} ({ss.class_name.class_name}-{ss.section.std_section})"

# -----------------------
# ATTENDANCE
# -----------------------
class AttendanceManager(models.Manager):
    def full_month_report(self, student_id, year, month):
        attendance_qs = self.filter(student_id=student_id, date__year=year, date__month=month)
        attendance_map = {att.date: att.get_status_display() for att in attendance_qs}
        num_days = monthrange(year, month)[1]
        report = []
        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            status = attendance_map.get(current_date, 'Not Marked')
            report.append({'date': current_date, 'status': status})
        return report

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('U', 'Undefined'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    time_marked = models.DateTimeField(auto_now_add=True)

    objects = AttendanceManager()

    def __str__(self):
        return f"{self.student} - {self.date}: {self.status}"

# -----------------------
# TEACHER ATTENDANCE
# -----------------------
class TeacherAttendanceManager(models.Manager):
    def teacher_monthly_report(self, teacher_id, year, month):
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        attendance_qs = self.filter(teacher_id=teacher_id, date__range=(start_date, end_date))
        attendance_map = {att.date: att.status for att in attendance_qs}

        report = []
        for day in days:
            status = attendance_map.get(day, 'Not Marked')
            report.append({'date': day, 'status': status})
        return report

class TeacherAttendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
    ]
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    time_marked = models.DateTimeField(auto_now_add=True)

    objects = TeacherAttendanceManager()

    def __str__(self):
        return f"{self.teacher} - {self.date}: {self.status}"

# -----------------------
# UNIFIED TEST SYSTEM
# -----------------------
class TestSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('monthly', 'Monthly Test'),
        ('session_exam', 'Session Exam'),
    ]
    name = models.CharField(max_length=100)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)
    year = models.CharField(max_length=4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.class_name.class_name}-{self.section.std_section}"

class Test(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name='tests')
    subject = models.CharField(max_length=50)
    test_name = models.CharField(max_length=50)
    total_marks = models.IntegerField()
    test_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.session.name} - {self.subject} ({self.test_name})"

class StudentTestResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    obtained_marks = models.FloatField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'test')

    def __str__(self):
        return f"{self.student} - {self.test}: {self.obtained_marks}"

# -----------------------
# FEE MODELS
# -----------------------
class Fee(models.Model):
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fee for {self.class_name.class_name} - {self.section.std_section}: {self.amount}"

class StudentFee(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_fees')
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name='student_fees')
    month = models.CharField(max_length=7)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    due_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'fee', 'month')
    
    def __str__(self):
        return f"{self.student} - {self.month} - PKR {self.amount_due}"

class FeePayment(models.Model):
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_fee.student} paid PKR {self.amount_paid} on {self.payment_date}"

class WhatsappMessage(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Message to {self.student} at {self.sent_at}"

class AttendanceNotification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    notification_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'attendance')
    
    def __str__(self):
        return f"Notification for {self.student} - {self.attendance.date}"

class MessageTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('fee_reminder', 'Fee Reminder'),
        ('attendance', 'Attendance Notification'),
        ('general', 'General Message'),
        ('exam', 'Exam Notification'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    message_text = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

class FeeUpdateLog(models.Model):
    ACTION_TYPES = [
        ('created', 'Fee Created'),
        ('submitted', 'Fee Submitted to Students'),
        ('payment', 'Fee Payment Recorded'),
        ('updated', 'Fee Updated'),
        ('deleted', 'Fee Deleted'),
    ]
    
    user = models.ForeignKey(Username, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, null=True, blank=True)
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} at {self.timestamp}"

# -----------------------
# USER ACTIVITY LOGGING
# -----------------------
class UserActivityLog(models.Model):
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
    ]
    
    user = models.ForeignKey(Username, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.timestamp}"

# -----------------------
# TIMETABLE
# -----------------------
class Timetable(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]
    
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.CharField(max_length=50)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('class_name', 'section', 'day_of_week', 'start_time')
    
    def __str__(self):
        return f"{self.class_name}-{self.section} | {self.subject} | {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class PromoteBatchForm(forms.Form):
    source_class = forms.ModelChoiceField(queryset=Class.objects.filter(is_active=True), label="From Class")
    source_section = forms.ModelChoiceField(queryset=Section.objects.none(), label="From Section")
    target_class = forms.ModelChoiceField(queryset=Class.objects.filter(is_active=True), label="To Class")
    target_section = forms.ModelChoiceField(queryset=Section.objects.none(), label="To Section")