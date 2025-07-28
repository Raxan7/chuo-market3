from django.shortcuts import render, redirect
from .forms import EmailSignupForm

def landing_page(request):
    submitted = False
    if request.method == 'POST':
        form = EmailSignupForm(request.POST)
        if form.is_valid():
            form.save()
            submitted = True
    else:
        form = EmailSignupForm()

    return render(request, 'landing/landing.html', {
        'form': form,
        'submitted': submitted
    })
