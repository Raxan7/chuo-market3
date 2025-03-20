from django.contrib.auth.models import AnonymousUser

def auth_status(request):
    return {
        'is_authenticated': not isinstance(request.user, AnonymousUser)
    }
