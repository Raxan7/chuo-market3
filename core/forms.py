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
    
    # Upload method selection field
    upload_method = forms.ChoiceField(
        choices=[
            ('local', '📱 Upload from Device (Local Storage)'),
            ('cloudinary', '☁️ Upload to Cloud Storage (Cloudinary)'),
        ],
        initial='local',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Choose where to store your blog thumbnail image'
    )
    
    # Cloudinary URL field for storing the cloud-hosted image
    thumbnail_cloudinary = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.HiddenInput(),
        help_text='Automatically populated by Cloudinary upload widget'
    )
    
    class Meta:
        model = Blog
        fields = ['title', 'content', 'category', 'thumbnail', 'thumbnail_cloudinary', 'upload_method']
        
    def clean(self):
        """Validate that at least one image upload method is used"""
        cleaned_data = super().clean()
        thumbnail = cleaned_data.get('thumbnail')
        thumbnail_cloudinary = cleaned_data.get('thumbnail_cloudinary')
        upload_method = cleaned_data.get('upload_method')
        
        # Ensure at least one image is provided
        if not thumbnail and not thumbnail_cloudinary:
            raise forms.ValidationError(
                'Please upload a blog thumbnail image using either local storage or Cloudinary.'
            )
        
        # Ensure the selected method has an image
        if upload_method == 'local' and not thumbnail:
            raise forms.ValidationError(
                'You selected local storage but did not upload an image. Either select an image or switch to Cloudinary.'
            )
        
        if upload_method == 'cloudinary' and not thumbnail_cloudinary:
            raise forms.ValidationError(
                'You selected cloud storage but did not upload an image. Please upload using the Cloudinary widget.'
            )
        
        return cleaned_data
        
    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get('thumbnail')
        if thumbnail:
            # Convert to WebP for better performance
            return convert_to_webp(thumbnail)
        return thumbnail


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
