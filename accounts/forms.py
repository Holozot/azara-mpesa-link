from django import forms
from .models import Account

# --- 1. REGISTRATION FORM ---
class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter Password',
        'class': 'form-control',
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password',
        'class': 'form-control',
    }))

    security_question = forms.ChoiceField(choices=Account.SECURITY_QUESTIONS, widget=forms.Select(attrs={'class': 'form-control'}))
    security_answer = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Your Answer (Hidden)', 'class': 'form-control' }))

    class Meta:
        model = Account
        # FIX 1: Added 'username' to this list so __init__ doesn't crash
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'email', 'password', 'security_question', 'security_answer']

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter Last Name'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Enter Phone Number'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'
        self.fields['username'].widget.attrs['placeholder'] = 'Enter Username'
        
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super(RegistrationForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")

        # Keep your specific password validations here if you want them
        if password:
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
            if not any(char.isdigit() for char in password):
                raise forms.ValidationError("Password must contain at least one number.")
            if not any(char.isupper() for char in password):
                raise forms.ValidationError("Password must contain at least one uppercase letter.")
            
        return cleaned_data

# --- 2. USER FORM ---
class UserForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    security_question = forms.ChoiceField(choices=Account.SECURITY_QUESTIONS, widget=forms.Select(attrs={'class': 'form-control'}))
    security_answer = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Account
        fields = ('first_name', 'last_name', 'phone_number', 'security_question', 'security_answer')