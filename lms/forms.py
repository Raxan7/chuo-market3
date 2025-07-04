"""
Forms for the LMS application
"""

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import re

from .models import (
    LMSProfile, Program, Course, CourseModule, CourseContent,
    Quiz, Question, MCQuestion, Choice, TF_Question, Essay_Question,
    Grade, InstructorRequest
)

# Import utility function from core app
from core.utils import clean_phone_number


class PhoneNumberField(forms.CharField):
    """Custom field for phone number validation"""
    def clean(self, value):
        value = super().clean(value)
        if not value:
            return None
        
        cleaned_phone = clean_phone_number(value)
        if not cleaned_phone:
            raise forms.ValidationError(_("Please enter a valid phone number with country code (e.g., +255123456789)"))
        
        return cleaned_phone


class LMSProfileForm(forms.ModelForm):
    """Form for updating an LMS user profile"""
    phone_number = PhoneNumberField(
        required=False,
        help_text=_("Enter phone number with country code (e.g., +255123456789)")
    )
    
    class Meta:
        model = LMSProfile
        fields = ['bio', 'profile_picture', 'phone_number']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class CourseForm(forms.ModelForm):
    """Form for creating and updating courses"""
    class Meta:
        model = Course
        fields = ['title', 'code', 'credit', 'summary', 'program', 
                  'level', 'year', 'semester', 'is_elective', 'instructors', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course title'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g. CS101'
            }),
            'credit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what students will learn in this course'
            }),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'is_elective': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'instructors': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CourseModuleForm(forms.ModelForm):
    """Form for creating and updating course modules"""
    class Meta:
        model = CourseModule
        fields = ['title', 'description', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class CourseContentForm(forms.ModelForm):
    """Form for creating and updating course content"""
    class Meta:
        model = CourseContent
        fields = ['title', 'content_type', 'document', 'video_url', 
                 'external_link', 'text_content', 'order'
        ]
        widgets = {
            'text_content': forms.Textarea(attrs={'rows': 6}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        
        # Validate that appropriate fields are filled based on content_type
        if content_type == 'document' and not cleaned_data.get('document'):
            self.add_error('document', _('Document is required for document content type'))
        elif content_type == 'video' and not cleaned_data.get('video_url'):
            self.add_error('video_url', _('Video URL is required for video content type'))
        elif content_type == 'link' and not cleaned_data.get('external_link'):
            self.add_error('external_link', _('External link is required for link content type'))
        elif content_type == 'text' and not cleaned_data.get('text_content'):
            self.add_error('text_content', _('Text content is required for text content type'))
        
        return cleaned_data


class QuizForm(forms.ModelForm):
    """Form for creating and updating quizzes"""
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'category', 'random_order',
                 'answers_at_end', 'exam_paper', 'single_attempt',
                 'pass_mark', 'draft', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class MCQuestionForm(forms.ModelForm):
    """Form for multiple choice questions"""
    class Meta:
        model = MCQuestion
        fields = ['content', 'figure', 'explanation', 'choice_order', 'order'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
        }


class ChoiceForm(forms.ModelForm):
    """Form for multiple choice answers"""
    class Meta:
        model = Choice
        fields = ['content', 'correct']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2}),
        }


class TFQuestionForm(forms.ModelForm):
    """Form for true/false questions"""
    class Meta:
        model = TF_Question
        fields = ['content', 'figure', 'explanation', 'correct', 'order'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
        }


class EssayQuestionForm(forms.ModelForm):
    """Form for essay questions"""
    class Meta:
        model = Essay_Question
        fields = ['content', 'figure', 'explanation', 'answer_type', 'order'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
        }


class GradeForm(forms.ModelForm):
    """Form for recording student grades"""
    class Meta:
        model = Grade
        fields = ['attendance', 'assignment', 'mid_exam', 'final_exam']
        

class CourseEnrollForm(forms.Form):
    """Form for students to enroll in courses"""
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        available_courses = kwargs.pop('available_courses', None)
        super().__init__(*args, **kwargs)
        
        if available_courses is not None:
            self.fields['course'].queryset = available_courses


class EssayAnswerForm(forms.Form):
    """Form for answering essay questions"""
    answer_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10}),
        required=False
    )
    answer_file = forms.FileField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        answer_text = cleaned_data.get('answer_text')
        answer_file = cleaned_data.get('answer_file')
        
        if not answer_text and not answer_file:
            raise forms.ValidationError(_('You must provide either text or file answer.'))
            
        return cleaned_data


class InstructorRequestForm(forms.ModelForm):
    """Form for requesting instructor status"""
    class Meta:
        model = InstructorRequest
        fields = ['reason', 'qualifications', 'cv']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'qualifications': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
