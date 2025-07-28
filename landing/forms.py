from django import forms
from .models import EmailSignup

class EmailSignupForm(forms.ModelForm):
    class Meta:
        model = EmailSignup
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Ingiza Email yako...',
                'class': 'input-email',
                'required': 'required',
                'type': 'email',
                'autocomplete': 'email',
            })
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Tafadhali ingiza email sahihi.')
        return email
