import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
sys.path.insert(0, '.')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

try:
    u = User.objects.get(username='saidi')
    print(f'ID: {u.id}')
    print(f'Username: {u.username}')
    print(f'Email: {u.email}')
    profile = getattr(u, 'lms_profile', None)
    if profile:
        print(f'Legal name: "{profile.legal_name}"')
        print(f'Has legal name: {profile.has_legal_name}')
    else:
        print('No LMSProfile')
except User.DoesNotExist:
    print('User "saidi" not found')
    for u2 in User.objects.all()[:20]:
        p = getattr(u2, 'lms_profile', None)
        print(f'  {u2.id}: {u2.username} (profile: {p is not None})')
