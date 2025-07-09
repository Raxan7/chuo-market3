from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import add_product, add_blog, create_blog, blog_list, blog_detail, products_by_category, about_us, contact_us, privacy_policy, terms_of_service
from .notifications import send_test_notification, send_notification_to_user, send_notification_to_group

urlpatterns = [
    path('', views.home, name='home'),
    
    # Information pages
    path('about/', about_us, name='about'),
    path('contact/', contact_us, name='contact'),
    path('privacy/', privacy_policy, name='privacy'),
    path('terms/', terms_of_service, name='terms'),
    
    # Existing paths
    path('product-detail/<int:pk>', views.product_detail, name='product-detail'),
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('cart/', views.view_cart, name='carts'),
    path('remove-cart/<int:pk>', views.remove_cart, name='remove-cart'),
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
    path('plus_cart', views.plus_cart, name='plus_cart'),  
    path('minus_cart/', views.minus_cart, name='minus_cart'),
    path('order_placed/', views.order_placed, name='order_placed'),
    path('orders/', views.orders, name='orders'),
    path('search/', views.search_bar, name='search'),
    path('get_cart_count/', views.get_cart_count, name='get_cart_count'),
    path('changepassword/', views.change_password, name='changepassword'),
    path('buynow/', views.buy_now, name='buy_now'),
    path('add-product/', add_product, name='add_product'),
    path('add-blog/', add_blog, name='add_blog'),
    path('create-blog/', create_blog, name='create_blog'),
    path('blogs/', blog_list, name='blog_list'),
    path('blogs/<int:pk>/', blog_detail, name='blog_detail'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('upload-payment-proof/<int:subscription_id>/', views.upload_payment_proof, name='upload_payment_proof'),
    path('category/<str:category>/', products_by_category, name='products-by-category'),
    
    # Push Notification URLs
    path('notifications/test/', send_test_notification, name='test_notification'),
    path('notifications/send/', send_notification_to_user, name='send_notification'),
    path('notifications/send/<int:user_id>/', send_notification_to_user, name='send_notification_to_user'),
    path('notifications/group/<str:group_name>/', send_notification_to_group, name='send_notification_to_group'),
]
