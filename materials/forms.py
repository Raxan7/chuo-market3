from django import forms
from .models import Material


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'description', 'software_url', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the software/tool name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what this software does and why it\'s useful...'
            }),
            'software_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/software'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean_software_url(self):
        url = self.cleaned_data.get('software_url')
        if url and not url.startswith(('http://', 'https://')):
            raise forms.ValidationError('URL must start with http:// or https://')
        return url