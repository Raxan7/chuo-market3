from django.shortcuts import redirect
from django.contrib import messages

def customer_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not hasattr(request.user, 'customer'):
            messages.warning(request, 'Please complete your profile before proceeding.')
            return redirect('profile')
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
