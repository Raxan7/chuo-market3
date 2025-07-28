from django.shortcuts import render, redirect
from .forms import EmailSignupForm
from .models import EmailSignup
from django.http import JsonResponse

def landing_page(request):
    submitted = False
    email = None
    if request.method == 'POST':
        form = EmailSignupForm(request.POST)
        if form.is_valid():
            # Save with purpose for this campaign
            email_signup = form.save(commit=False)
            email_signup.purpose = "enrolling in the digital marketing course"
            email_signup.save()
            submitted = True
            email = email_signup.email
            # Render a countdown page before redirect
            return render(request, 'landing/countdown.html', {
                'redirect_url': 'https://chuosmart.com/lms/courses/ujasiriamali-wa-kidijitali-kwa-kutumia-chuosmart/direct/',
                'seconds': 3,
                'email': email
            })
    else:
        form = EmailSignupForm()

    return render(request, 'landing/landing.html', {
        'form': form,
        'submitted': submitted
    })
