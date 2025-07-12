from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import RegistrationForm, LoginForm, ProductForm, BlogForm, SubscriptionForm, SubscriptionPaymentForm, CustomerProfileForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from .universities_colleges_tanzania import universities_data
from chatbotapp.models import ChatMessage, UnauthenticatedChatMessage
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import timedelta
from django.utils.decorators import method_decorator
from core.decorators.customer_required import customer_required, phone_required
import re
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

def get_cart_count(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
    else:
        cart_count = 0
    return JsonResponse({'cart_count': cart_count})

def home(request):
    user = request.user
    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Set session expiration times
    request.session.set_expiry(3600)  # 1 hour of constant use
    request.session.set_expiry(1800)  # 30 minutes if inactive

    is_authenticated = user.is_authenticated
    if is_authenticated:
        messages = list(ChatMessage.objects.filter(user=user))
        # request.session.flush()  # Comment out this line to prevent session flush on login
        customers = Customer.objects.filter(user=user).exists()
        
        # Check if we should show the dashboard notification (only once)
        if 'dashboard_notification_shown' not in request.session:
            # Set the session flag so we don't show it again
            request.session['dashboard_notification_shown'] = True
            # Set a session variable to show the modal that will be picked up by our context processor
            request.session['show_dashboard_modal'] = True
    else:
        messages = request.session.get('messages', [])
        if not messages:
            messages = list(UnauthenticatedChatMessage.objects.filter(session_key=session_key))
            request.session['messages'] = [{'user_message': msg.user_message, 'bot_response': msg.bot_response} for msg in messages]
            request.session.modified = True
        customers = False

    # Get all products and randomize them
    products = list(Product.objects.all().order_by('?'))  # '?' randomizes the order
    banners = list(Banners.objects.all())
    
    # You can still get category-specific products for category pages if needed
    # but for home page, we'll use randomized products
    # Get the dashboard notification status from session
    show_dashboard_modal = request.session.pop('show_dashboard_modal', False)
    
    context = {
        'customers': customers,
        'products': products, 
        'banners': banners,
        'show_dashboard_modal': show_dashboard_modal,
        'messages': messages,
        'is_authenticated': is_authenticated,
    }
    return render(request, 'app/home.html', context)

def product_detail(request, pk=None, slug=None):
    """
    View product details using either slug or pk
    """
    # Get product using either slug or pk
    if slug:
        product = get_object_or_404(Product, slug=slug)
    else:
        product = get_object_or_404(Product, pk=pk)
    
    # Clean product description if needed (remove outer curly braces)
    if product.description and product.description.startswith('{') and product.description.endswith('}'):
        product.description = product.description[1:-1]  # Remove first and last characters (curly braces)
    
    customer = product.user.customer
    user = request.user
    
    if isinstance(user, AnonymousUser):
        product_cart = None
    else:
        product_cart = Cart.objects.filter(user=user, product=product.pk).exists()
    
    return render(request, 'app/productdetail.html', {
        'product': product, 
        'product_cart': product_cart, 
        'user': user, 
        'customer': customer
    })


@login_required(login_url='login')
@customer_required
def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    Cart.objects.create(user=user, product=product)
    return HttpResponseRedirect(reverse('carts'))



@login_required(login_url='login')
@customer_required
def view_cart(request):
    user = request.user
    carts = Cart.objects.filter(user=user)
    shipping_amount = 5.0
    cart_items_with_price = [{'item': cart.product, 'price': cart.product.price, 'quantity': cart.quantity} for cart in carts]
    amount = sum(cart.product.price * cart.quantity for cart in carts)
    total_amount = amount + shipping_amount
    return render(request, 'app/addtocart.html', {'carts': cart_items_with_price, 'total_amount': total_amount, 'shipping_amount': shipping_amount, 'amount': amount})

@login_required(login_url='login')
@customer_required
def remove_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product:
        print('Product Found')
    else:
        print('Product not Found')
    cart_item = Cart.objects.filter(product=product, user=request.user).first()

    if cart_item:
        print('Cart Found')
        cart_item.delete()

    return redirect(reverse('carts'))

@login_required(login_url='login')
@customer_required
def plus_cart(request):
    if request.method == 'GET':
        pid = request.GET.get('pid')
        cart_item = get_object_or_404(Cart, user=request.user, product__id=pid)
        cart_item.quantity += 1
        cart_item.save()

        amount = cart_item.product.price * cart_item.quantity
        shipping_amount = 5.0
        total_amount = amount + shipping_amount

        return JsonResponse({'status': 'ok', 'quantity': cart_item.quantity, 'total_amount': total_amount, 'amount': amount})

@login_required(login_url='login')
@customer_required
def minus_cart(request):
    if request.method == 'GET':
        pid = request.GET.get('pid')
        cart_item = get_object_or_404(Cart, user=request.user, product__id=pid)
        cart_item.quantity -= 1
        cart_item.save()

        amount = cart_item.product.price * cart_item.quantity
        shipping_amount = 5.0
        total_amount = amount + shipping_amount

        return JsonResponse({'status': 'ok', 'quantity': cart_item.quantity, 'total_amount': total_amount, 'amount':amount})
        


@login_required(login_url='login')
def profile(request):
    user = request.user
    UNIVERSITY_CHOICES = [(uni['name'], uni['name']) for uni in universities_data]
    COLLEGE_CHOICES = [(college, college) for uni in universities_data for college in uni['colleges']]
    
    # Get or create customer instance for the form
    customer, created = Customer.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            # Redirect to add_product page after successful profile update
            return redirect('add_product')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomerProfileForm(instance=customer)
    
    # Get user's products
    user_products = Product.objects.filter(user=user).order_by('-created_at')

    context = {
        'user': user,
        'form': form,
        'UNIVERSITY_CHOICES': UNIVERSITY_CHOICES,
        'COLLEGE_CHOICES': COLLEGE_CHOICES,
        'universities_data': universities_data,
        'user_products': user_products,
    }
    return render(request, 'app/profile.html', context)

@login_required(login_url='login')
def address(request):
    addresses = Customer.objects.filter(user=request.user)
    context = {'addresses': addresses}
    return render(request, 'app/address.html', context)

@login_required(login_url='login')
def orders(request):
    user = request.user
    orders = OrderPlaced.objects.filter(user=user)
    return render(request, 'app/orders.html', {'orders': orders})

@login_required(login_url='login')
@customer_required
def order_placed(request):
    user = request.user
    customer_id = request.GET.get("customer_id")
    customer = get_object_or_404(Customer, id=customer_id)
    
    product_id = request.GET.get("product_id")
    quantity = int(request.GET.get("quantity", 1))

    if product_id:
        product = get_object_or_404(Product, id=product_id)
        product_price = product.price  
        OrderPlaced.objects.create(user=user, customer=customer, product=product, quantity=quantity, price=str(product_price * quantity + 5))
    else:
        carts = Cart.objects.filter(user=user)
        for cart in carts:
            product_price = cart.product.price  
            OrderPlaced.objects.create(user=user, customer=customer, product=cart.product, quantity=cart.quantity, price=str(product_price * cart.quantity + 5))
            cart.delete()
        print('OrderPlaced DONE')

    return redirect('orders')


def mobile(request):
 return render(request, 'app/mobile.html')

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Set session to never expire
                request.session.set_expiry(31536000)  # 1 year in seconds
                # Check if user needs to complete their profile
                if not hasattr(user, 'customer') or not user.customer:
                    messages.info(request, 'Please complete your profile information.')
                    return redirect('profile')
                messages.success(request, 'You have successfully logged in.')
                return redirect('home')  # Redirect to the desired page after login
            else:
                messages.error(request, 'Invalid username or password.')
                form.add_error(None, 'Invalid username or password.')
        else:
            logger.warning("Form data is invalid: %s", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LoginForm()
    
    return render(request, 'app/login.html', {'form': form})

def customerregistration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()  # Save the user
                # Customer profile will be created by signal handler
                
                # Log success
                logger.info("User %s registered successfully", user.username)
                
                # Show success message
                messages.success(request, "Registration successful! You can now log in.")
                return redirect('login')
            except Exception as e:
                logger.error("Error occurred during user registration: %s", str(e))
                messages.error(request, f"Registration failed: {str(e)}")
        else:
            logger.warning("Form data is invalid: %s", form.errors)
            # Display specific field errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegistrationForm()
    return render(request, 'app/customerregistration.html', {'form': form})

@login_required(login_url='login')
@customer_required
def checkout(request, product_id=None, quantity=1):
    user = request.user
    addresses = Customer.objects.filter(user=user)
    
    if request.method == "POST":
        address_id = request.POST.get('customer_id')
        return redirect(reverse('order_placed') + f'?customer_id={address_id}&product_id={product_id}&quantity={quantity}')
    
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        order_summary = [{
            'product': product,
            'quantity': quantity,
            'total_price': product.price * quantity,
        }]
        total_amount = product.price * quantity
    else:
        cart_items = Cart.objects.filter(user=user)
        order_summary = [{
            'product': item.product,
            'quantity': item.quantity,
            'total_price': item.product.price * item.quantity,
        } for item in cart_items]
        total_amount = sum(item['total_price'] for item in order_summary)

    context = {
        'addresses': addresses,
        'order_summary': order_summary,
        'total_amount': total_amount,
        'product_id': product_id,
        'quantity': quantity,
    }
    
    return render(request, 'app/checkout.html', context)


@login_required(login_url='login')
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


def search_bar(request):
    if request.method == "POST":
        query = request.POST.get('search')
        print(query)
        products = Product.objects.filter(title__icontains=query)
        return render(request, 'app/search.html', {'products': products, "query": query})
    else:
        return render(request, 'app/home.html')

@login_required(login_url='login')
def change_password(request):
    if request.method == "POST":
        current_pass = request.POST.get('current_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        if not request.user.check_password(current_pass):
            messages.error(request, 'Current password is incorrect.')
        elif new_pass != confirm_pass:
            messages.error(request, 'New passwords do not match.')
        else:
            user = request.user
            user.set_password(new_pass)
            user.save()
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')  
    return render(request, 'app/changepassword.html')


@login_required(login_url='login')
def buy_now(request):
    user = request.user
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        return redirect('checkout_with_product', product_id=product.id, quantity=1)

@login_required(login_url='login')
@customer_required
@phone_required
@login_required(login_url='login')
@phone_required
def add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            try:
                product = product_form.save(commit=False)
                product.user = request.user
                # Ensure description is properly encoded
                if product.description:
                    # This ensures emojis are properly saved
                    product.description = product.description
                product_form.save()
                return redirect('home')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error saving product with emojis: {e}")
                messages.error(request, "There was an error saving your product. Please try again.")
    else:
        product_form = ProductForm()
    return render(request, 'app/add_product.html', {'product_form': product_form})

@login_required(login_url='login')
@customer_required
def add_blog(request):
    if request.method == 'POST':
        blog_form = BlogForm(request.POST, request.FILES)
        print(blog_form.is_valid())
        if blog_form.is_valid():
            blog = blog_form.save(commit=False)
            blog.author = request.user
            blog_form.save()
            return redirect('blog_list')  # Replace with your success URL
    else:
        blog_form = BlogForm()
    return render(request, 'app/add_blog.html', {'blog_form': blog_form})

@login_required(login_url='login')
@customer_required
def create_blog(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            return redirect('blog_list')
    else:
        form = BlogForm()
    return render(request, 'app/create_blog.html', {'form': form})

def blog_list(request):
    # Order by most recent first rather than random order for consistency
    blogs = Blog.objects.all().order_by('-created_at')
    return render(request, 'app/blog_list.html', {'blogs': blogs})

def deep_clean_html_content(content):
    """
    Aggressively clean HTML content from TinyMCE with problematic formatting.
    This function specifically handles the case where HTML tags and data attributes
    are showing up as text in the rendered output.
    """
    import re
    import html
    import logging
    
    logger = logging.getLogger(__name__)
    logger.debug("Starting deep_clean_html_content")
    
    if not content:
        logger.debug("Content is empty")
        return content
    
    # Debug the input content
    logger.debug(f"Original content starts with: {content[:100]}...")
    logger.debug(f"Original content ends with: ...{content[-100:]}")
    logger.debug(f"Content length: {len(content)}")
    logger.debug(f"Content starts with curly brace: {content.startswith('{')}")
    logger.debug(f"Content ends with curly brace: {content.endswith('}')}")
    
    # Process the content
    cleaned_content = content
    
    # Special debug for the example we're seeing
    if "{<blockquote data-start=" in content[:100]:
        logger.debug("DETECTED SPECIFIC PROBLEMATIC PATTERN!")
        
    # EXACT PATTERN MATCHING - Check for the specific pattern we're seeing
    if content.startswith('{<') and '<blockquote data-start=' in content[:100]:
        logger.debug("Using direct pattern extraction approach")
        # Try a different approach - extract all HTML without the outer braces
        try:
            # If the content is wrapped in {} and contains HTML tags with data attributes,
            # we need to process it differently
            if content.startswith('{') and content.endswith('}'):
                # Remove surrounding braces
                content_without_braces = content[1:-1]
                logger.debug(f"Extracted content without braces: {content_without_braces[:50]}...")
                
                # We'll return the content directly for rendering as HTML
                return content_without_braces
        except Exception as e:
            logger.error(f"Error in direct pattern extraction: {e}")
    
    # STEP 1: Remove JSON-like wrapping
    if cleaned_content.startswith('{') and ('<' in cleaned_content):
        logger.debug("Removing JSON-like wrapping")
        if cleaned_content.endswith('}'):
            cleaned_content = cleaned_content[1:-1].strip()
            logger.debug(f"Removed both braces, content now starts with: {cleaned_content[:50]}...")
        else:
            # Just remove the opening brace if closing one isn't found
            cleaned_content = cleaned_content[1:].strip()
            logger.debug(f"Removed opening brace only, content now starts with: {cleaned_content[:50]}...")
    
    # STEP 2: Remove all data-* attributes (aggressive pattern)
    original_len = len(cleaned_content)
    cleaned_content = re.sub(r'\s+data-[a-zA-Z0-9_-]+=["\'][^"\']*["\']', '', cleaned_content)
    logger.debug(f"Removed data attributes, content changed by {original_len - len(cleaned_content)} characters")
    
    # STEP 3: Remove problematic class attributes
    class_patterns = [
        r'\s+class=["\']_[^"\']*["\']',
        r'\s+class=["\'](?:_tableContainer_[^"\']*|_tableWrapper_[^"\']*|group\s+flex\s+w-fit\s+flex-col-reverse)["\']',
        r'\s+class=["\'][^"\']*flex[^"\']*["\']'
    ]
    
    for pattern in class_patterns:
        original_len = len(cleaned_content)
        cleaned_content = re.sub(pattern, '', cleaned_content)
        logger.debug(f"Applied class pattern, content changed by {original_len - len(cleaned_content)} characters")
    
    # STEP 4: Remove other problematic attributes
    other_attr_patterns = [
        r'\s+tabindex=["\'][^"\']*["\']',
        r'\s+data-col-size=["\'][^"\']*["\']'
    ]
    
    for pattern in other_attr_patterns:
        original_len = len(cleaned_content)
        cleaned_content = re.sub(pattern, '', cleaned_content)
        logger.debug(f"Applied other attribute pattern, content changed by {original_len - len(cleaned_content)} characters")
    
    # STEP 5: Handle special edge case where entire HTML content is wrapped in a pair of curly braces
    # This happens sometimes with TinyMCE and specific formats
    curly_brace_pattern = r'^\{(<[^>]+>.*</[^>]+>)\}$'
    curly_match = re.search(curly_brace_pattern, cleaned_content, re.DOTALL)
    if curly_match:
        logger.debug("Found curly brace pattern match")
        cleaned_content = curly_match.group(1)
        logger.debug(f"Extracted content now starts with: {cleaned_content[:50]}...")
    
    # Try more specific extraction for our case
    if cleaned_content.startswith('{<blockquote') or cleaned_content.startswith('<blockquote data-start='):
        logger.debug("Trying specialized extraction for blockquote pattern")
        # This is a targeted fix for the specific pattern we're seeing
        html_pattern = r'(\{)?(<(?:blockquote|p|div|h[1-6]|ul|ol|li)[\s\S]*>[\s\S]*?</(?:blockquote|p|div|h[1-6]|ul|ol|li)>)(\})?'
        html_matches = re.findall(html_pattern, cleaned_content, re.DOTALL)
        
        if html_matches:
            logger.debug(f"Found {len(html_matches)} HTML blocks to extract")
            extracted_html = []
            
            for match in html_matches:
                # Take the middle part (the HTML)
                extracted_html.append(match[1])
            
            # Join them together
            cleaned_content = ''.join(extracted_html)
            logger.debug(f"Extracted HTML content now starts with: {cleaned_content[:50]}...")
    
    # STEP 6: Replace any doubled open/close tags that might cause issues
    doubled_tags = [r'<(p|div|span|strong|em)>\s*<\1>', r'</([^>]+)>\s*</\1>']
    for pattern in doubled_tags:
        original_len = len(cleaned_content)
        cleaned_content = re.sub(pattern, r'<\1>', cleaned_content)
        logger.debug(f"Applied doubled tags pattern, content changed by {original_len - len(cleaned_content)} characters")
    
    # STEP 7: Unescape any HTML entities
    cleaned_content = html.unescape(cleaned_content)
    
    # Final debug
    logger.debug(f"Final cleaned content starts with: {cleaned_content[:100]}...")
    logger.debug(f"Final cleaned content length: {len(cleaned_content)}")
    
    return cleaned_content

def blog_detail(request, slug):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"Processing blog_detail for slug: {slug}")
    blog = get_object_or_404(Blog, slug=slug)
    
    # Try to detect if this blog has serious formatting issues
    has_severe_issues = False
    has_emergency_redirect = False
    original_content = blog.content
    
    # Check if the user wants to use the simple template
    use_simple_template = request.GET.get('simple', 'false').lower() == 'true'
    template_name = 'app/blog_detail_simple.html' if use_simple_template else 'app/blog_detail.html'
    
    # Check for serious content issues
    if blog.content:
        # Keep original content for debug info
        original_content_preview = blog.content[:200] + ('...' if len(blog.content) > 200 else '')
        
        # Check for severe issues that might need emergency handling
        if ((blog.content.startswith('{') and '<' in blog.content[:100]) or
            'data-start=' in blog.content[:200]):
            
            has_severe_issues = True
            # For admins, show the emergency view option
            if request.user.is_staff or request.user.is_superuser:
                has_emergency_redirect = True
    
    # Add debug flag to context to enable browser console debugging
    context = {
        'blog': blog,
        'debug_mode': True,
        'has_severe_issues': has_severe_issues,
        'has_emergency_redirect': has_emergency_redirect,
        'original_content_preview': original_content_preview if 'original_content_preview' in locals() else ""
    }
    
    return render(request, template_name, context)


@login_required(login_url='login')
@customer_required
def subscribe(request):
    user = request.user
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription')
        subscription = get_object_or_404(Subscription, id=subscription_id)
        form = SubscriptionPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.customer = user.customer
            payment.subscription = subscription
            payment.save()
            messages.success(request, 'Your payment proof has been submitted. Please wait for admin verification.')
            return redirect('profile')
    else:
        form = SubscriptionPaymentForm()

    subscriptions = []
    for subscription in Subscription.objects.all().order_by('-id'):
        benefits = [benefit.strip().capitalize() for benefit in subscription.benefits.split(',')]
        subscriptions.append({
            'id': subscription.id,
            'level': subscription.level,
            'price': subscription.price,
            'benefits': benefits
        })

    return render(request, 'app/subscribe.html', {'form': form, 'subscriptions': subscriptions})

@login_required(login_url='login')
@customer_required
def upload_payment_proof(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    if request.method == 'POST':
        form = SubscriptionPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.customer = request.user.customer
            payment.subscription = subscription
            payment.save()
            messages.success(request, 'Your payment proof has been submitted. Please wait for admin verification.')
            return redirect('profile')
    else:
        form = SubscriptionPaymentForm()
    return render(request, 'app/upload_payment_proof.html', {'form': form, 'subscription': subscription})

def products_by_category(request, category):
    products = Product.objects.filter(category=category)
    return render(request, 'app/products_by_category.html', {'products': products, 'category': category})

def clean_phone_number(phone):
    """
    Clean and validate phone number to ensure it's properly formatted.
    Returns None if invalid, formatted phone number if valid.
    """
    if not phone or phone.strip() == "":
        return None
    
    # Remove all non-digit characters except the + sign at the beginning
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # If doesn't start with +, add the default Tanzania code
    if not cleaned.startswith('+'):
        if cleaned.startswith('0'):
            cleaned = '+255' + cleaned[1:]
        elif not re.match(r'^\d{9,15}$', cleaned):
            return None
        else:
            cleaned = '+' + cleaned
    
    # Validate the length (international format: country code + number)
    if not re.match(r'^\+\d{9,14}$', cleaned):
        return None
        
    return cleaned[:15]  # Ensure it doesn't exceed the max length

def robots_txt(request):
    """
    Serve robots.txt file with dynamic host information
    """
    host = request.get_host()
    scheme = request.scheme
    context = {
        'request': request,
        'host': host,
        'scheme': scheme,
    }
    return render(request, 'robots.txt', context, content_type='text/plain')

# Page views for About Us, Contact Us, and Privacy Policy
def about_us(request):
    """Render the About Us page"""
    return render(request, 'app/about.html')

def contact_us(request):
    """Render the Contact Us page and handle form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_content = request.POST.get('message')
        newsletter = request.POST.get('newsletter') == 'on'
        
        # Create formatted message
        full_message = f"""
        New contact message from ChuoSmart website:
        
        Name: {name}
        Email: {email}
        Subject: {subject}
        Newsletter Signup: {"Yes" if newsletter else "No"}
        
        Message:
        {message_content}
        """
        
        # Send email
        try:
            send_mail(
                f'ChuoSmart Contact: {subject}',
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                ['support@chuosmart.com'],  # Replace with your actual email
                fail_silently=False,
            )
            
            # Handle newsletter signup if checked
            if newsletter:
                # Check if email already exists in subscribers
                if not NewsletterSubscriber.objects.filter(email=email).exists():
                    NewsletterSubscriber.objects.create(
                        name=name,
                        email=email,
                        source='contact_form'
                    )
            
            messages.success(request, 'Thank you for reaching out! We will get back to you soon.')
            return redirect('contact')
        except Exception as e:
            messages.error(request, 'Sorry, there was an error sending your message. Please try again later.')
            
    return render(request, 'app/contact.html')

def privacy_policy(request):
    """Render the Privacy Policy page"""
    return render(request, 'app/privacy.html')

def terms_of_service(request):
    """Render the Terms of Service page"""
    return render(request, 'app/terms.html')

def clean_all_blog_content(request):
    """
    Admin utility view to clean all blog content in the database.
    This is a one-time fix for all blogs with problematic HTML content.
    """
    # Only allow staff/admin to run this
    if not request.user.is_staff:
        return redirect('home')
    
    from .models import Blog
    blogs = Blog.objects.filter(is_markdown=False)
    cleaned_count = 0
    
    for blog in blogs:
        if blog.content:
            original_content = blog.content
            cleaned_content = deep_clean_html_content(original_content)
            
            # Only update if content has actually changed
            if cleaned_content != original_content:
                blog.content = cleaned_content
                blog.save(update_fields=['content'])
                cleaned_count += 1
    
    from django.contrib import messages
    messages.success(request, f"Successfully cleaned {cleaned_count} blog posts.")
    return redirect('admin:core_blog_changelist')

def debug_blog_content(request, blog_id):
    """
    Debug utility view that shows the original and cleaned versions of blog content side by side.
    Only accessible to staff users.
    """
    import logging
    import json
    from django.http import JsonResponse, HttpResponseForbidden
    
    # Only allow staff to access this debug tool
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Staff access required")
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Debug blog content for ID: {blog_id}")
    
    try:
        blog = Blog.objects.get(pk=blog_id)
        
        # Get original content
        original_content = blog.content
        
        # Get cleaned content using our function
        cleaned_content = deep_clean_html_content(original_content)
        
        # Specialized direct fix - if direct method is specified in the URL
        if request.GET.get('direct_fix') == '1':
            logger.debug("Using direct fix method")
            if original_content.startswith('{') and original_content.endswith('}'):
                direct_fixed = original_content[1:-1]  # Simply remove outer braces
                
                # Save this version if save parameter is provided
                if request.GET.get('save') == '1':
                    logger.debug("Saving direct fix to database")
                    blog.content = direct_fixed
                    blog.save(update_fields=['content'])
                    return JsonResponse({
                        "status": "saved", 
                        "message": "Content fixed and saved to database"
                    })
                
                # Just preview the changes
                return JsonResponse({
                    "original_length": len(original_content),
                    "direct_fixed_length": len(direct_fixed),
                    "original_preview": original_content[:500],
                    "direct_fixed_preview": direct_fixed[:500]
                })
        
        # If save parameter is provided, save the cleaned content
        if request.GET.get('save') == '1':
            logger.debug("Saving cleaned content to database")
            blog.content = cleaned_content
            blog.save(update_fields=['content'])
            return JsonResponse({"status": "saved", "message": "Content cleaned and saved to database"})
        
        # Compare content and provide detailed debugging info
        return JsonResponse({
            "blog_id": blog.id,
            "blog_title": blog.title,
            "original_length": len(original_content),
            "cleaned_length": len(cleaned_content),
            "starts_with_brace": original_content.startswith('{'),
            "ends_with_brace": original_content.endswith('}'),
            "original_preview": original_content[:500],
            "cleaned_preview": cleaned_content[:500]
        })
    
    except Blog.DoesNotExist:
        logger.error(f"Blog with ID {blog_id} not found")
        return JsonResponse({"error": "Blog not found"}, status=404)
    except Exception as e:
        logger.error(f"Error debugging blog content: {e}")
        return JsonResponse({"error": str(e)}, status=500)

def emergency_blog_view(request, slug):
    """
    Emergency view that directly strips curly braces from blog content.
    """
    blog = get_object_or_404(Blog, slug=slug)
    
    # Create a copy of the blog for the template
    from copy import deepcopy
    display_blog = deepcopy(blog)
    
    # Direct brace removal
    if display_blog.content.startswith('{') and display_blog.content.endswith('}'):
        display_blog.content = display_blog.content[1:-1]
    
    return render(request, 'app/blog_detail.html', {'blog': display_blog, 'emergency_mode': True})

def blog_detail_emergency(request, slug):
    """
    Emergency view for blogs with problematic HTML content.
    This view directly processes the blog content, ensuring proper display
    and offers several repair options for admin users.
    """
    import logging
    import re
    import html
    import json
    from django.http import JsonResponse
    
    logger = logging.getLogger(__name__)
    
    # Get the blog post or return 404
    blog = get_object_or_404(Blog, slug=slug)
    
    # Process the save request if applicable (admin only)
    if request.method == 'POST' and request.user.is_superuser:
        # Different save options for different fixing strategies
        if 'save_fixed_content' in request.POST:
            # Option 1: Use the basic emergency fix (just remove braces)
            original_content = blog.content
            content = original_content
            
            # Step 1: Remove braces if content is wrapped in them
            if content.startswith('{') and content.endswith('}'):
                content = content[1:-1]
                
            # Step 2: Remove data attributes
            content = re.sub(r'\s+data-[a-zA-Z0-9_-]+=["|\'][^"\']*["|\']', '', content)
            
            # Save the fixed content to the database
            blog.content = content
            blog.save(update_fields=['content'])
            
            # Redirect to normal view with success message
            messages.success(request, "Blog content has been fixed and saved successfully.")
            return redirect('blog_detail', slug=slug)
            
        elif 'save_aggressive_fix' in request.POST:
            # Option 2: Use more aggressive cleaning approach
            from core.management.commands.fix_blog_content_advanced import Command
            cmd = Command()
            
            # Get the original content
            original_content = blog.content
            
            # Fix content using the command's fix_content method
            fixed_content = cmd.fix_content(original_content)
            
            # Save the fixed content to the database
            blog.content = fixed_content
            blog.save(update_fields=['content'])
            
            messages.success(request, "Blog content has been aggressively cleaned and saved.")
            return redirect('blog_detail', slug=slug)
            
        elif 'recreate_content' in request.POST:
            # Option 3: Full recreation, preserving only important elements
            from core.management.commands.fix_blog_content_advanced import Command
            cmd = Command()
            
            # Use the recreation method
            cmd._recreate_blog_content(blog, verbose=True)
            
            messages.success(request, "Blog content has been recreated from scratch.")
            return redirect('blog_detail', slug=slug)
            
        elif 'raw_content' in request.POST:
            # Option 4: Admin provided raw content
            raw_content = request.POST.get('raw_html_content', '')
            if raw_content.strip():
                blog.content = raw_content
                blog.save(update_fields=['content'])
                messages.success(request, "Custom HTML content has been saved.")
                return redirect('blog_detail', slug=slug)
    
    # Process the blog content for display
    content = blog.content
    fixed_content = ""
    
    if content:
        # Try different approaches to fix the content for display
        # Approach 1: Handle content wrapped in braces
        if content.startswith('{') and '<' in content and '}' in content[-10:]:
            fixed_content = content[1:-1] if content.endswith('}') else content[1:]
        # Approach 2: Use the full clean function
        elif 'data-start=' in content or '<blockquote data-start=' in content:
            fixed_content = deep_clean_html_content(content)
        else:
            # For other cases, just use the content directly
            fixed_content = content
    
    # Get the raw content for display in the admin edit form
    raw_content = blog.content
    
    # Extract images for preservation (in case we need to recreate content)
    image_tags = []
    if content:
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*/?>'
        image_tags = re.findall(img_pattern, content)
    
    # Return the emergency template with various options
    return render(request, 'app/blog_detail_emergency.html', {
        'blog': blog,
        'fixed_content': fixed_content,
        'raw_content': raw_content,
        'image_tags': image_tags,
        'is_admin': request.user.is_superuser or request.user.is_staff,
        'has_braces': content.startswith('{') and content.endswith('}') if content else False,
        'has_data_attrs': 'data-start=' in content if content else False,
        'content_length': len(content) if content else 0
    })

from core.decorators.product_owner import owns_product

@login_required
@customer_required
@owns_product
def edit_product(request, pk=None, slug=None):
    """
    Edit a product - only the owner of the product can edit it
    """
    # Get product using either slug or pk
    if slug:
        product = get_object_or_404(Product, slug=slug)
    else:
        product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Your product has been updated successfully.")
            return redirect('product-detail', slug=product.slug if product.slug else product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'app/edit_product.html', {
        'form': form,
        'product': product,
    })

@login_required
@customer_required
@owns_product
def delete_product(request, pk=None, slug=None):
    """
    Delete a product - only the owner of the product can delete it
    """
    # Get product using either slug or pk
    if slug:
        product = get_object_or_404(Product, slug=slug)
    else:
        product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # Store information for confirmation message
        product_title = product.title
        
        # Delete the product
        product.delete()
        
        messages.success(request, f"Your product '{product_title}' has been deleted successfully.")
        return redirect('profile')  # Redirect to user profile after deletion
    
    return render(request, 'app/delete_product_confirm.html', {
        'product': product,
    })

@login_required
@customer_required
def edit_blog(request, slug):
    """
    Edit a blog - only the author of the blog can edit it
    """
    blog = get_object_or_404(Blog, slug=slug)
    
    # Check if the current user is the author of the blog
    if blog.author != request.user:
        messages.error(request, "You can only edit blogs that you've authored.")
        return redirect('blog_detail', slug=blog.slug)
    
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, "Your blog has been updated successfully.")
            return redirect('blog_detail', slug=blog.slug)
    else:
        form = BlogForm(instance=blog)
    
    return render(request, 'app/edit_blog.html', {
        'form': form,
        'blog': blog,
    })

@login_required
@customer_required
def delete_blog(request, slug):
    """
    Delete a blog - only the author of the blog can delete it
    """
    blog = get_object_or_404(Blog, slug=slug)
    
    # Check if the current user is the author of the blog
    if blog.author != request.user:
        messages.error(request, "You can only delete blogs that you've authored.")
        return redirect('blog_detail', slug=blog.slug)
    
    if request.method == 'POST':
        # Store information for confirmation message
        blog_title = blog.title
        
        # Delete the blog
        blog.delete()
        
        messages.success(request, f"Your blog '{blog_title}' has been deleted successfully.")
        return redirect('user_dashboard')  # We'll create this view later
    
    return render(request, 'app/delete_blog_confirm.html', {
        'blog': blog,
    })

@login_required
def user_dashboard(request):
    """
    User dashboard showing all user content - products, blogs, and talents
    """
    user = request.user
    
    # Get user's content
    user_products = Product.objects.filter(user=user).order_by('-created_at')
    user_blogs = Blog.objects.filter(author=user).order_by('-created_at')
    
    # Get user talents from the talents app
    from talents.models import Talent
    user_talents = Talent.objects.filter(user=user).order_by('-created_at')
    
    # Default active tab
    active_tab = request.GET.get('tab', 'products')
    
    context = {
        'user': user,
        'user_products': user_products,
        'user_blogs': user_blogs,
        'user_talents': user_talents,
        'active_tab': active_tab,
        'product_count': user_products.count(),
        'blog_count': user_blogs.count(),
        'talent_count': user_talents.count(),
    }
    return render(request, 'app/dashboard.html', context)

@login_required(login_url='login')
def subscription_view(request):
    """
    View for managing user subscriptions
    """
    user = request.user
    # Get or create customer instance
    customer, created = Customer.objects.get_or_create(user=user)
    
    # Get customer's current subscription if it exists
    try:
        current_subscription = customer.subscription
        subscription_level = current_subscription.level if current_subscription else "Free"
    except (AttributeError, ObjectDoesNotExist):
        subscription_level = "Free"
    
    # Handle subscription form submission
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.customer = customer
            subscription.save()
            messages.success(request, "Subscription updated successfully.")
            return redirect('profile')
    else:
        form = SubscriptionForm()
    
    context = {
        'user': user,
        'form': form,
        'subscription_level': subscription_level,
    }
    
    return render(request, 'app/subscription.html', context)