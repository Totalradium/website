from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from bri.models import Username, StudentTestResult  # Import your model

class CreateUserForm(forms.ModelForm):
    class Meta:
        model = Username
        fields = ['username', 'password', 'role']
    
    password = forms.CharField(widget=forms.PasswordInput, min_length=8, label='Password')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        role = self.cleaned_data.get('role')

        # Apply strong password validation only for Admin and Teacher
        if role in ['admin', 'teacher']:
            try:
                # Use Django's built-in password validation logic
                validate_password(password)  # This will raise ValidationError if password doesn't meet the criteria
            except ValidationError as e:
                raise forms.ValidationError(f'Password is too weak. {str(e)}')
        
        # No password validation for students
        return password

class StudentTestResultForm(forms.ModelForm):
    class Meta:
        model = StudentTestResult
        fields = ["student", "test", "obtained_marks", "remarks"]
