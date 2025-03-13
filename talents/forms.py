from django import forms
from .models import Talent, Comment

class TalentForm(forms.ModelForm):
    class Meta:
        model = Talent
        fields = ['title', 'description', 'category', 'media']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter the title of your talent'}),
            'description': forms.Textarea(attrs={'placeholder': 'Describe your talent'}),
            'category': forms.Select(attrs={'placeholder': 'Select a category'}),
            'media': forms.ClearableFileInput(attrs={'placeholder': 'Upload media'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Add a comment'}),
        }
