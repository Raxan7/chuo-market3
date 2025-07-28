# affiliates/urls.py
from django.urls import path
from .views import (
    affiliate_dashboard, 
    request_payout, 
    register_affiliate,
    referral_link,
    affiliate_stats,
    generate_referral_link,
    affiliate_settings,
    payout_history,
    referral_list,
    affiliate_terms
)

app_name = 'affiliates'

urlpatterns = [
    path('dashboard/', affiliate_dashboard, name='dashboard'),
    path('register/', register_affiliate, name='register'),
    path('settings/', affiliate_settings, name='settings'),
    path('stats/', affiliate_stats, name='stats'),
    path('referrals/', referral_list, name='referrals'),
    path('payouts/', payout_history, name='payouts'),
    path('request-payout/', request_payout, name='request_payout'),
    path('terms/', affiliate_terms, name='terms'),
    
    # Referral link generation
    path('generate-link/', generate_referral_link, name='generate_link'),
    path('link/<str:code>/', referral_link, name='referral_link'),
    
    # These will be automatically handled by the middleware
    path('r/<str:username>/', referral_link, name='user_referral'),
    path('r/<str:username>/<str:product_id>/', referral_link, name='product_referral'),
]