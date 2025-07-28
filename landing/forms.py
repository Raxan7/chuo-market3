from django import forms
from .models import EmailSignup

class EmailSignupForm(forms.ModelForm):
    class Meta:
        model = EmailSignup
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Ingiza Email yako...',
                'class': 'input-email'
            })
        }
