from django import forms
from .models import Account

class RegistrationForm(forms.ModelForm):
    # Add password fields manually because they need special handling (hiding text)
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter Password',
        'class': 'form-control',
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password',
        'class': 'form-control',
    }))

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'username' ,'phone_number', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter Last Name'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Enter Phone Number'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'
        
        # Add styling for the new Username field
        self.fields['username'].widget.attrs['placeholder'] = 'Enter Username'
        
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    # Custom clean method to check if passwords match
    def clean(self):
        cleaned_data = super(RegistrationForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # 1. Check if passwords match
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")

        # 2. Check Minimum Length
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")

        # 3. Check for Digit
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one number.")

        # 4. Check for Uppercase
        if not any(char.isupper() for char in password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
            
        return cleaned_data