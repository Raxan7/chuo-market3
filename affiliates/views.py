from django.contrib.auth.decorators import login_required
from .models import Affiliate, Referral
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
import uuid
import json


@login_required
def affiliate_dashboard(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    referrals = Referral.objects.filter(affiliate=affiliate).select_related('user_course', 'user_course__course')
    
    context = {
        'affiliate': affiliate,
        'referrals': referrals,
        'total_earnings': sum([r.commission_earned for r in referrals]),
        'unpaid_balance': sum([r.commission_earned for r in referrals if not r.is_paid]),
    }
    return render(request, 'affiliates/dashboard.html', context)


@login_required
def register_affiliate(request):
    if request.method == 'POST':
        # Check if user already is an affiliate
        affiliate, created = Affiliate.objects.get_or_create(user=request.user)
        
        if created:
            # Generate a unique referral code if not provided
            if not affiliate.referral_code:
                affiliate.referral_code = f"{request.user.username}-{uuid.uuid4().hex[:6]}"
                affiliate.save()
            
            return redirect('affiliates:dashboard')
        else:
            return redirect('affiliates:dashboard')
    
    return render(request, 'affiliates/register.html')


@login_required
def request_payout(request):
    affiliate = Affiliate.objects.get(user=request.user)
    
    if affiliate.balance > 0:
        # Integrate with Stripe/PayPal here
        print(f"Paying out ${affiliate.balance} to {affiliate.user.email}")
        affiliate.balance = 0
        affiliate.save()
        return HttpResponse("Payout request submitted!")
    return HttpResponse("No balance available for payout.")


def referral_link(request, username=None, product_id=None):
    # This view handles incoming referral links
    if username:
        try:
            referring_user = User.objects.get(username=username)
            affiliate = Affiliate.objects.get(user=referring_user)
            
            # Store referral info in session
            request.session['referrer_id'] = affiliate.id
            if product_id:
                request.session['referred_product'] = product_id
                
            # Redirect to product page if product_id is provided
            if product_id:
                return redirect('lms:course_detail', pk=product_id)
            
            # Otherwise redirect to homepage
            return redirect('core:home')
        except (User.DoesNotExist, Affiliate.DoesNotExist):
            pass
    
    return redirect('core:home')


@login_required
def affiliate_stats(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    # Get basic stats
    total_referrals = Referral.objects.filter(affiliate=affiliate).count()
    successful_referrals = Referral.objects.filter(affiliate=affiliate, is_converted=True).count()
    total_earnings = sum([r.commission_earned for r in Referral.objects.filter(affiliate=affiliate)])
    
    context = {
        'affiliate': affiliate,
        'total_referrals': total_referrals,
        'successful_referrals': successful_referrals,
        'conversion_rate': (successful_referrals / total_referrals * 100) if total_referrals else 0,
        'total_earnings': total_earnings,
    }
    
    return render(request, 'affiliates/stats.html', context)


@login_required
@require_POST
def generate_referral_link(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return JsonResponse({'error': 'You are not registered as an affiliate'}, status=400)
    
    data = json.loads(request.body)
    product_id = data.get('product_id')
    
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    if product_id:
        referral_url = f"{base_url}/affiliate/r/{request.user.username}/{product_id}/"
    else:
        referral_url = f"{base_url}/affiliate/r/{request.user.username}/"
    
    return JsonResponse({'referral_url': referral_url})


@login_required
def affiliate_settings(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    if request.method == 'POST':
        # Update affiliate settings
        payout_email = request.POST.get('payout_email')
        if payout_email:
            affiliate.payout_email = payout_email
            affiliate.save()
        
        return redirect('affiliates:settings')
    
    context = {
        'affiliate': affiliate,
    }
    
    return render(request, 'affiliates/settings.html', context)


@login_required
def payout_history(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    # In a real app, you'd have a PayoutHistory model
    # For now, we'll just use referrals that have been paid
    payouts = Referral.objects.filter(affiliate=affiliate, is_paid=True)
    
    context = {
        'affiliate': affiliate,
        'payouts': payouts,
        'total_paid': sum([r.commission_earned for r in payouts]),
    }
    
    return render(request, 'affiliates/payouts.html', context)


@login_required
def referral_list(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    referrals = Referral.objects.filter(affiliate=affiliate).select_related('user_course', 'user_course__course')
    
    context = {
        'affiliate': affiliate,
        'referrals': referrals,
    }
    
    return render(request, 'affiliates/referrals.html', context)


def affiliate_terms(request):
    return render(request, 'affiliates/terms.html')