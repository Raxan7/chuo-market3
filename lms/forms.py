"""
Forms for the LMS application
"""

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE
import re

from .models import (
    LMSProfile, Program, Course, CourseModule, CourseContent,
    Quiz, Question, MCQuestion, Choice, TF_Question, Essay_Question,
    Grade, InstructorRequest, PaymentMethod
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
    

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'payment_number', 'instructions', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. M-Pesa, Tigo Pesa, Bank Transfer'}),
            'payment_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 07XXXXXXXX'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any special instructions for payment'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make program field required only if programs exist
        if not Program.objects.exists():
            self.fields['program'].required = False
            
        # Check if it's a university course - only require university fields for university course type
        if self.instance and self.instance.pk and self.instance.course_type == 'university':
            # For university courses, these fields are required
            for field in ['code', 'credit', 'program', 'level', 'year', 'semester']:
                self.fields[field].required = True
        elif self.instance and self.instance.pk and self.instance.course_type == 'general':
            # For general courses, these fields are not required
            for field in ['code', 'credit', 'program', 'level', 'year', 'semester']:
                self.fields[field].required = False
            
    def clean(self):
        cleaned_data = super().clean()
        course_type = cleaned_data.get('course_type')
        
        # Validate that appropriate fields are filled based on course_type
        if course_type == 'university':
            university_fields = ['code', 'credit', 'program', 'level', 'year', 'semester']
            for field in university_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _(f'{field.title()} is required for university courses'))
        
        # Validate price for paid courses
        is_free = cleaned_data.get('is_free')
        price = cleaned_data.get('price')
        if is_free is False:
            # Paid course must have a positive price
            if price is None or price <= 0:
                self.add_error('price', _('Price must be greater than zero for paid courses'))
        else:
            # Free course should have zero price
            cleaned_data['price'] = 0
        
        return cleaned_data
            
    class Meta:
        model = Course
        fields = ['title', 'course_type', 'code', 'credit', 'summary', 'program', 
                  'level', 'year', 'semester', 'is_elective', 'is_free', 'price', 'instructors', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course title'
            }),
            'course_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_course_type'
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
            'summary': TinyMCE(attrs={
                'class': 'form-control tinymce',
                'placeholder': 'Describe what students will learn in this course',
                'data-custom-formatting': 'true'
            }),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'is_elective': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.00', 'step': '0.01'}),
            'instructors': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CourseModuleForm(forms.ModelForm):
    """Form for creating and updating course modules"""
    class Meta:
        model = CourseModule
        fields = ['title', 'description', 'order']
        widgets = {
            'description': TinyMCE(attrs={'class': 'form-control tinymce', 'data-custom-formatting': 'true'}),
        }


class CourseContentForm(forms.ModelForm):
    """Form for creating and updating course content"""
    class Meta:
        model = CourseContent
        fields = ['title', 'content_type', 'document', 'video_url', 
                 'external_link', 'text_content', 'order'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content_type': forms.Select(attrs={'class': 'form-select'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=example'}),
            'external_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'text_content': TinyMCE(attrs={'class': 'form-control tinymce', 'data-custom-formatting': 'true'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
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


class ProgramForm(forms.ModelForm):
    """Form for creating a new program"""
    class Meta:
        model = Program
        fields = ['title', 'summary']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter program title'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Provide a brief description of this program'
            }),
        }
