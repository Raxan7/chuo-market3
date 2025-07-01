"""
Forms for the LMS application
"""

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import (
    LMSProfile, Program, Course, CourseModule, CourseContent,
    Quiz, Question, MCQuestion, Choice, TF_Question, Essay_Question,
    Grade
)


class LMSProfileForm(forms.ModelForm):
    """Form for updating an LMS user profile"""
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
                  'level', 'year', 'semester', 'is_elective', 'image']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 4}),
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
                 'external_link', 'text_content', 'order']
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
        fields = ['content', 'figure', 'explanation', 'choice_order', 'order']
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
        fields = ['content', 'figure', 'explanation', 'correct', 'order']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
        }


class EssayQuestionForm(forms.ModelForm):
    """Form for essay questions"""
    class Meta:
        model = Essay_Question
        fields = ['content', 'figure', 'explanation', 'answer_type', 'order']
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
