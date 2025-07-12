from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from core.models import Product

def owns_product(view_func):
    """
    Decorator to check if the user is the owner of the product.
    Usage: @owns_product
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Get product by slug or pk
        slug = kwargs.get('slug')
        pk = kwargs.get('pk')
        
        try:
            if slug:
                product = Product.objects.get(slug=slug)
            elif pk:
                product = Product.objects.get(pk=pk)
            else:
                messages.error(request, "Invalid product reference.")
                return redirect('home')
            
            # Check if user is the owner
            if request.user != product.user:
                messages.error(request, "You can only manage your own products.")
                return redirect('product-detail', slug=product.slug if product.slug else product.pk)
                
            # User is the owner, proceed with view
            return view_func(request, *args, **kwargs)
            
        except Product.DoesNotExist:
            raise Http404("Product does not exist")
            
    return _wrapped_view
