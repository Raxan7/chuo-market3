from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Blog, Subscription, SubscriptionPayment, Customer
from tinymce.widgets import TinyMCE
from .utils import clean_phone_number

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'category', 'description', 'price', 'discount_price', 'image']


class BlogForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows':50,'class': 'form-control'}))
    
    class Meta:
        model = Blog
        fields = ['title', 'content', 'thumbnail']


class SubscriptionForm(forms.Form):
    subscription = forms.ModelChoiceField(queryset=Subscription.objects.all(), empty_label="Select Subscription Level")


class SubscriptionPaymentForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPayment
        fields = ['payment_proof']


class CustomerProfileForm(forms.ModelForm):
    """Form for updating customer profile information"""
    phone_number = forms.CharField(
        required=True, 
        max_length=15,
        help_text="Required. Enter phone number with country code (e.g., +255123456789)",
        widget=forms.TextInput(attrs={'placeholder': '+255123456789'})
    )
    
    class Meta:
        model = Customer
        fields = ['name', 'is_university_student', 'university', 'college', 'block_number', 'room_number', 'phone_number']
        widgets = {
            'is_university_student': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_university_student'}),
        }
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        
        if not phone:
            raise forms.ValidationError("Phone number is required to add products on our marketplace")
            
        cleaned_phone = clean_phone_number(phone)
        
        if not cleaned_phone:
            raise forms.ValidationError("Please enter a valid phone number with country code (e.g., +255123456789)")
            
        return cleaned_phone
