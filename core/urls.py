from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import (
    add_product, add_blog, create_blog, blog_list, blog_detail, products_by_category, 
    about_us, contact_us, privacy_policy, terms_of_service, clean_all_blog_content, 
    edit_blog, delete_blog, user_dashboard
)
from .notifications import send_test_notification, send_notification_to_user, send_notification_to_group
from .help_views import help_center

urlpatterns = [
    path('', views.home, name='home'),
    path('marketplace/', views.marketplace, name='marketplace'),
    
    # Information pages
    path('about/', about_us, name='about'),
    path('contact/', contact_us, name='contact'),
    path('privacy/', privacy_policy, name='privacy'),
    path('terms/', terms_of_service, name='terms'),
    path('help/', help_center, name='help_center'),
    
    # Product detail paths - support both slug and pk for backward compatibility
    path('product/<slug:slug>/', views.product_detail, name='product-detail'),
    path('product-detail/<int:pk>/', views.product_detail, name='product-detail-by-id'),  # Keep old URL pattern for backwards compatibility
    
    # Product edit/delete paths
    path('product/<slug:slug>/edit/', views.edit_product, name='edit-product'),
    path('product/<int:pk>/edit/', views.edit_product, name='edit-product-by-id'),
    path('product/<slug:slug>/delete/', views.delete_product, name='delete-product'),
    path('product/<int:pk>/delete/', views.delete_product, name='delete-product-by-id'),
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('cart/', views.view_cart, name='carts'),
    path('remove-cart/<int:pk>/', views.remove_cart, name='remove-cart'),
    path('buy/', views.buy_now, name='buy-now'),
    path('profile/', views.profile, name='profile'),
    path('address/', views.address, name='address'),
    path('orders/', views.orders, name='orders'),
    path('mobile/', views.mobile, name='mobile'),
    path('logout/', views.user_logout, name='logout'),
    path('login/', views.user_login, name='login'),
    path('registration/', views.customerregistration, name='customerregistration'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/<int:product_id>/<int:quantity>/', views.checkout, name='checkout_with_product'),
    path('plus_cart/', views.plus_cart, name='plus_cart'),  
    path('minus_cart/', views.minus_cart, name='minus_cart'),
    path('order_placed/', views.order_placed, name='order_placed'),
    path('orders/', views.orders, name='orders'),
    path('search/', views.search_bar, name='search'),
    path('get_cart_count/', views.get_cart_count, name='get_cart_count'),
    path('changepassword/', views.change_password, name='changepassword'),
    path('buynow/', views.buy_now, name='buy_now'),
    
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='app/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='app/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='app/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='app/password_reset_complete.html'), name='password_reset_complete'),
    
    path('add-product/', add_product, name='add_product'),
    path('add-blog/', add_blog, name='add_blog'),
    path('create-blog/', create_blog, name='create_blog'),
    
    # Category URLs
    path('category/<str:category>/', products_by_category, name='products-by-category'),
    
    # Blog URLs
    path('blogs/', blog_list, name='blog_list'),
    path('blogs/<slug:slug>/', blog_detail, name='blog_detail'),
    path('blogs/<slug:slug>/edit/', edit_blog, name='edit-blog'),
    path('blogs/<slug:slug>/delete/', delete_blog, name='delete-blog'),
    
    # Dashboard
    path('dashboard/', user_dashboard, name='user_dashboard'),
    
    # Subscription
    path('subscription/', views.subscription_view, name='subscribe'),
    
    # Push Notification URLs
    path('notifications/test/', send_test_notification, name='test_notification'),
    path('notifications/send/', send_notification_to_user, name='send_notification'),
    path('notifications/send/<int:user_id>/', send_notification_to_user, name='send_notification_to_user'),
    path('notifications/group/<str:group_name>/', send_notification_to_group, name='send_notification_to_group'),
    
    # Admin utility URLs
    path('debug/blog/<int:blog_id>/', views.debug_blog_content, name='debug_blog_content'),
    path('admin/clean-blogs/', clean_all_blog_content, name='clean_all_blog_content'),
    
    # Emergency URL for problematic blog posts
    path('emergency/blog/<slug:slug>/', views.blog_detail_emergency, name='emergency_blog_view'),
]
