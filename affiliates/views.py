from django.contrib.auth.decorators import login_required
from .models import Affiliate, Referral, PayoutRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum
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
        # The model generates a unique affiliate_code on first save.
        Affiliate.objects.get_or_create(user=request.user)
        return redirect('affiliates:dashboard')
    
    return render(request, 'affiliates/register.html')


@login_required
@require_POST
def request_payout(request):
    with transaction.atomic():
        affiliate = Affiliate.objects.select_for_update().get(user=request.user)
        reserved = PayoutRequest.objects.filter(
            affiliate=affiliate,
            status__in=[PayoutRequest.PayoutStatus.PENDING, PayoutRequest.PayoutStatus.APPROVED],
        ).aggregate(total=Sum('amount'))['total'] or 0
        available = affiliate.balance - reserved

        if available <= 0:
            return HttpResponse("No balance available for payout.", status=400)

        payment_method = affiliate.payment_method or 'manual_review'
        PayoutRequest.objects.create(
            affiliate=affiliate,
            amount=available,
            payment_method=payment_method,
            payment_details=affiliate.payment_details or {},
        )

    return HttpResponse("Payout request submitted for review.")


def referral_link(request, code=None, username=None, product_id=None):
    # This view handles both canonical affiliate-code links and legacy username links.
    if code or username:
        try:
            if code:
                affiliate = Affiliate.objects.select_related('user').get(affiliate_code=code)
                referring_user = affiliate.user
            else:
                referring_user = User.objects.get(username=username)
                affiliate = Affiliate.objects.get(user=referring_user)
            
            # Store referral info in session
            request.session['referrer_id'] = affiliate.id
            if product_id:
                request.session['referred_product'] = product_id
                
            # Redirect to product page if product_id is provided (using slug lookup)
            if product_id:
                from lms.models import Course
                try:
                    course = Course.objects.get(pk=product_id)
                    return redirect('lms:course_detail', slug=course.slug)
                except Course.DoesNotExist:
                    pass
            
            # Otherwise redirect to homepage
            return redirect('home')
        except (User.DoesNotExist, Affiliate.DoesNotExist):
            pass
    
    return redirect('home')


@login_required
def affiliate_stats(request):
    try:
        affiliate = Affiliate.objects.get(user=request.user)
    except Affiliate.DoesNotExist:
        return render(request, 'affiliates/not_affiliate.html')
    
    # Get basic stats
    total_referrals = Referral.objects.filter(affiliate=affiliate).count()
    successful_referrals = Referral.objects.filter(affiliate=affiliate, converted_at__isnull=False).count()
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
        payment_method = (request.POST.get('payment_method') or '').strip()[:50]
        phone_number = (request.POST.get('phone_number') or '').strip()[:15]
        payout_email = (request.POST.get('payout_email') or '').strip()

        details = dict(affiliate.payment_details or {})
        if payout_email:
            details['email'] = payout_email
        if phone_number:
            details['phone'] = phone_number

        affiliate.payment_method = payment_method or affiliate.payment_method
        affiliate.phone_number = phone_number or affiliate.phone_number
        affiliate.payment_details = details
        affiliate.save(update_fields=['payment_method', 'phone_number', 'payment_details'])
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
    
    payouts = PayoutRequest.objects.filter(affiliate=affiliate).order_by('-requested_at')
    total_paid = payouts.filter(status=PayoutRequest.PayoutStatus.PAID).aggregate(
        total=Sum('amount')
    )['total'] or 0

    context = {
        'affiliate': affiliate,
        'payouts': payouts,
        'total_paid': total_paid,
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