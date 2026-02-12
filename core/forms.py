from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Blog, Subscription, SubscriptionPayment, Customer
from tinymce.widgets import TinyMCE
from core.utils import clean_phone_number
from .image_utils import convert_to_webp, optimize_image

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
    description = forms.CharField(
        widget=TinyMCE(
            attrs={
                'cols': 80, 
                'rows': 30, 
                'class': 'form-control'
            }
        )
    )
    
    class Meta:
        model = Product
        fields = ['title', 'category', 'description', 'price', 'discount_price', 'image']
        
    def clean_description(self):
        description = self.cleaned_data.get('description')
        # This ensures the description is properly handled as UTF-8
        # and can safely contain emojis
        if description:
            return description
        return description
        
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Convert to WebP for better performance
            return convert_to_webp(image)
        return image


class BlogForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows':50,'class': 'form-control'}))
    
    # Upload method selection
    upload_method = forms.ChoiceField(
        choices=[('local', 'Upload from Device (Local Storage)'), 
                 ('cloudinary', 'Upload to Cloudinary (Cloud Storage)')],
        initial='local',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Choose where to store your image. Local is traditional file upload, Cloudinary is cloud-based with automatic optimization."
    )
    
    # Cloudinary direct upload field
    thumbnail_cloudinary = forms.ImageField(
        required=False,
        help_text="Upload image to Cloudinary (cloud storage with automatic optimization)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    
    class Meta:
        model = Blog
        fields = ['title', 'content', 'thumbnail', 'category']
        widgets = {
            'thumbnail': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Technology, Education, Business'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing and Cloudinary image exists, set method to cloudinary
        if self.instance and self.instance.pk and self.instance.thumbnail_cloudinary:
            self.fields['upload_method'].initial = 'cloudinary'
    
    def clean(self):
        cleaned_data = super().clean()
        upload_method = cleaned_data.get('upload_method')
        thumbnail = cleaned_data.get('thumbnail')
        thumbnail_cloudinary = cleaned_data.get('thumbnail_cloudinary')
        
        # Validate that at least one image is provided for new posts
        if not self.instance.pk:  # New blog post
            if upload_method == 'local' and not thumbnail:
                if not thumbnail_cloudinary:
                    raise forms.ValidationError("Please upload a thumbnail image.")
            elif upload_method == 'cloudinary' and not thumbnail_cloudinary:
                if not thumbnail:
                    raise forms.ValidationError("Please upload a thumbnail image to Cloudinary.")
        
        return cleaned_data
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        upload_method = self.cleaned_data.get('upload_method')
        thumbnail_cloudinary = self.cleaned_data.get('thumbnail_cloudinary')
        
        # Handle Cloudinary upload
        if upload_method == 'cloudinary' and thumbnail_cloudinary:
            import cloudinary.uploader
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                thumbnail_cloudinary,
                folder='blog_thumbnails',
                transformation=[
                    {'quality': 'auto', 'fetch_format': 'auto'},
                    {'width': 1200, 'height': 630, 'crop': 'limit'}
                ]
            )
            # Store the Cloudinary public_id
            instance.thumbnail_cloudinary = upload_result['public_id']
        
        # Handle local upload (existing behavior)
        elif upload_method == 'local' and self.cleaned_data.get('thumbnail'):
            # Convert to WebP for better performance (existing functionality)
            instance.thumbnail = convert_to_webp(self.cleaned_data.get('thumbnail'))
        
        if commit:
            instance.save()
        return instance


class SubscriptionForm(forms.Form):
    subscription = forms.ModelChoiceField(queryset=Subscription.objects.all(), empty_label="Select Subscription Level")


class SubscriptionPaymentForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPayment
        fields = ['payment_proof']
        
    def clean_payment_proof(self):
        payment_proof = self.cleaned_data.get('payment_proof')
        if payment_proof:
            # Optimize the image
            return optimize_image(payment_proof)
        return payment_proof


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
