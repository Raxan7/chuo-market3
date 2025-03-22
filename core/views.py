from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import RegistrationForm, LoginForm, ProductForm, BlogForm, SubscriptionForm
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
from core.decorators.customer_required import customer_required

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
    else:
        messages = request.session.get('messages', [])
        if not messages:
            messages = list(UnauthenticatedChatMessage.objects.filter(session_key=session_key))
            request.session['messages'] = [{'user_message': msg.user_message, 'bot_response': msg.bot_response} for msg in messages]
            request.session.modified = True
        customers = False

    mobile = list(Product.objects.filter(category='M'))
    electronics = list(Product.objects.filter(category__iexact='El'))
    books = list(Product.objects.filter(category='B'))
    cloth = list(Product.objects.filter(category='C'))
    accessorie = list(Product.objects.filter(category='AC'))
    products = list(Product.objects.all())
    banners = list(Banners.objects.all())
    context = {
        'customers': customers,
        'products': products, 
        'mobile': mobile,
        'electronics': electronics,
        'books': books,
        'cloth': cloth,
        'accessorie': accessorie,
        'banners': banners,
        'messages': messages,
        'is_authenticated': is_authenticated,
    }
    return render(request, 'app/home.html', context)

def product_detail(request, pk):
    product = Product.objects.get(pk=pk)
    customer = product.user.customer
    user = request.user
    if isinstance(user, AnonymousUser):
        product_cart = None
    else:
        product_cart = Cart.objects.filter(user=user, product=product.pk).exists()
    return render(request, 'app/productdetail.html', {'product': product, 'product_cart': product_cart, 'user': user, 'customer': customer})


@login_required(login_url='/login/')
@customer_required
def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    Cart.objects.create(user=user, product=product)
    return HttpResponseRedirect(reverse('carts'))



@login_required(login_url='/login/')
@customer_required
def view_cart(request):
    user = request.user
    carts = Cart.objects.filter(user=user)
    shipping_amount = 5.0
    cart_items_with_price = [{'item': cart.product, 'price': cart.product.price, 'quantity': cart.quantity} for cart in carts]
    amount = sum(cart.product.price * cart.quantity for cart in carts)
    total_amount = amount + shipping_amount
    return render(request, 'app/addtocart.html', {'carts': cart_items_with_price, 'total_amount': total_amount, 'shipping_amount': shipping_amount, 'amount': amount})

@login_required(login_url='/login/')
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

@login_required(login_url='/login/')
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

@login_required(login_url='/login/')
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
        


@login_required(login_url='/login/')
def profile(request):
    user = request.user
    UNIVERSITY_CHOICES = [(uni['name'], uni['name']) for uni in universities_data]
    COLLEGE_CHOICES = [(college, college) for uni in universities_data for college in uni['colleges']]
    
    if request.method == 'POST':
        name = request.POST.get('name')
        university = request.POST.get('university')
        college = request.POST.get('college')
        block_number = request.POST.get('block_number')
        room_number = request.POST.get('room_number')

        customer, created = Customer.objects.update_or_create(
            user=user,
            defaults={
                'name': name,
                'university': university,
                'college': college,
                'block_number': block_number,
                'room_number': room_number,
            }
        )
        messages.success(request, "Profile updated successfully.")

    context = {
        'user': user,
        'UNIVERSITY_CHOICES': UNIVERSITY_CHOICES,
        'COLLEGE_CHOICES': COLLEGE_CHOICES,
        'universities_data': universities_data,
    }
    return render(request, 'app/profile.html', context)

@login_required(login_url='/login/')
def address(request):
    addresses = Customer.objects.filter(user=request.user)
    context = {'addresses': addresses}
    return render(request, 'app/address.html', context)

@login_required(login_url='/login/')
def orders(request):
    user = request.user
    orders = OrderPlaced.objects.filter(user=user)
    return render(request, 'app/orders.html', {'orders': orders})

@login_required(login_url='/login/')
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
                messages.success(request, 'You have successfully logged in.')
                return redirect('home')  # Redirect to the desired page after login
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            logger.warning("Form data is invalid: %s", form.errors)
    else:
        form = LoginForm()
    
    return render(request, 'app/login.html', {'form': form})

def customerregistration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()  # Save the user
                logger.info("User %s registered successfully.", user.username)
                return redirect('login')
            except Exception as e:
                logger.error("Error occurred during user registration: %s", str(e))
        else:
            logger.warning("Form data is invalid: %s", form.errors)
    else:
        form = RegistrationForm()
    return render(request, 'app/customerregistration.html', {'form': form})

@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


def search_bar(request):
    if request.method == "POST":
        query = request.POST.get('search')
        print(query)
        products = Product.objects.filter(title__icontains=query)
        return render(request, 'app/search.html', {'products': products, "query": query})
    else:
        return render(request, 'app/home.html')

@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def buy_now(request):
    user = request.user
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        return redirect('checkout_with_product', product_id=product.id, quantity=1)

@login_required
@customer_required
def add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            product = product_form.save(commit=False)
            product.user = request.user
            product_form.save()
            return redirect('home')
    else:
        product_form = ProductForm()
    return render(request, 'app/add_product.html', {'product_form': product_form})

@login_required
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

@login_required
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
    blogs = Blog.objects.all()
    return render(request, 'app/blog_list.html', {'blogs': blogs})

def blog_detail(request, pk):
    blog = Blog.objects.get(pk=pk)
    return render(request, 'app/blog_detail.html', {'blog': blog})


@login_required(login_url='/login/')
@customer_required
def subscribe(request):
    user = request.user
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.cleaned_data['subscription']
            customer = user.customer
            customer.subscription = subscription
            customer.save()
            messages.success(request, 'Subscription updated successfully.')
            return redirect('profile')
    else:
        form = SubscriptionForm()
    
    subscriptions = []
    for subscription in form.fields['subscription'].queryset:
        benefits = [benefit.strip().capitalize() for benefit in subscription.benefits.split(',')]
        subscriptions.append({
            'id': subscription.id,
            'level': subscription.level,
            'price': subscription.price,
            'benefits': benefits
        })
    
    return render(request, 'app/subscribe.html', {'form': form, 'subscriptions': subscriptions})