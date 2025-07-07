from django.shortcuts import redirect
from django.contrib import messages

def customer_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not hasattr(request.user, 'customer'):
            messages.warning(request, 'Please complete your profile before proceeding.')
            return redirect('profile')
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

def phone_required(view_func):
    """
    Decorator to ensure a user has provided their phone number before accessing a view.
    """
    def _wrapped_view_func(request, *args, **kwargs):
        # First check if customer profile exists
        if not hasattr(request.user, 'customer'):
            messages.warning(request, 'Please complete your profile before proceeding.')
            return redirect('profile')
        
        # Then check if phone number exists
        if not request.user.customer.phone_number:
            messages.warning(request, 'Please add your phone number in your profile before adding products.')
            return redirect('profile')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
