from webpush import send_user_notification, send_group_notification
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.contrib import messages

@login_required
def send_test_notification(request):
    """
    Send a test notification to the current user or group
    Renders a form for testing notifications if GET, processes the form if POST
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if request.method == 'GET':
        return render(request, 'app/test_notification.html')
    
    # Handle POST request to send notification
    head = request.POST.get('head', 'ChuoSmart Notification')
    body = request.POST.get('body', 'You have a new notification')
    icon = request.POST.get('icon', '/static/app/images/logo.png')
    url = request.POST.get('url', request.build_absolute_uri('/'))
    target = request.POST.get('target', 'self')
    
    payload = {
        'head': head,
        'body': body,
        'icon': icon,
        'url': url,
    }
    
    success = True
    
    try:
        if target == 'self':
            # Send to current user
            send_user_notification(user=request.user, payload=payload, ttl=1000)
            messages.success(request, 'Test notification sent successfully to your browser!')
        elif target == 'all' and request.user.is_staff:
            # Send to all users (staff only)
            users = User.objects.filter(is_active=True)
            for user in users:
                send_user_notification(user=user, payload=payload, ttl=1000)
            messages.success(request, f'Notification sent to all {users.count()} active users!')
        elif target == 'group' and request.user.is_staff:
            # Send to a specific group (staff only)
            group_name = request.POST.get('group')
            send_group_notification(group_name=group_name, payload=payload, ttl=1000)
            messages.success(request, f'Notification sent to group: {group_name}!')
        else:
            messages.error(request, 'You do not have permission for this action')
            success = False
    except Exception as e:
        messages.error(request, f'Error sending notification: {str(e)}')
        success = False
    
    return render(request, 'app/test_notification.html', {'success': success})

@login_required
@require_POST
@csrf_exempt
def send_notification_to_user(request, user_id=None):
    """
    Send a notification to a specific user or the current user
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Default to current user if no user_id provided
    target_user = request.user
    if user_id:
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'User not found'
            }, status=404)
    
    # Get notification data from POST request
    head = request.POST.get('head', 'ChuoSmart Notification')
    body = request.POST.get('body', 'You have a new notification')
    icon = request.POST.get('icon', '/static/app/images/logo.png')
    url = request.POST.get('url', request.build_absolute_uri('/'))
    
    payload = {
        'head': head,
        'body': body,
        'icon': icon,
        'url': url,
    }
    
    # Send the notification
    send_user_notification(user=target_user, payload=payload, ttl=1000)
    
    return JsonResponse({
        'status': 'success',
        'message': 'Notification sent successfully!'
    })

def send_notification_to_group(request, group_name):
    """
    Send a notification to a group of users
    Admin access only
    """
    if not request.user.is_staff:
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        }, status=403)
    
    # Get notification data from POST request
    head = request.POST.get('head', 'ChuoSmart Notification')
    body = request.POST.get('body', 'You have a new notification')
    icon = request.POST.get('icon', '/static/app/images/logo.png')
    url = request.POST.get('url', request.build_absolute_uri('/'))
    
    payload = {
        'head': head,
        'body': body,
        'icon': icon,
        'url': url,
    }
    
    # Send the notification to the group
    send_group_notification(group_name=group_name, payload=payload, ttl=1000)
    
    return JsonResponse({
        'status': 'success',
        'message': f'Notification sent to group {group_name} successfully!'
    })

# Utility functions to be called from other parts of the application

def notify_new_product(user, product):
    """Notify followers when a user posts a new product"""
    from core.models import UserProfile
    
    # Get followers of the user
    followers = UserProfile.objects.filter(following=user)
    
    payload = {
        'head': 'New Product Available',
        'body': f'{user.username} just listed: {product.title}',
        'icon': product.image.url if product.image else '/static/app/images/logo.png',
        'url': f'/product/{product.id}/',
    }
    
    for follower in followers:
        send_user_notification(user=follower.user, payload=payload, ttl=1000)

def notify_new_message(user, sender, message_preview):
    """Notify user about a new chat message"""
    payload = {
        'head': f'New message from {sender.username}',
        'body': message_preview[:100] + ('...' if len(message_preview) > 100 else ''),
        'icon': '/static/app/images/logo.png',
        'url': '/messages/',
    }
    
    send_user_notification(user=user, payload=payload, ttl=1000)

def notify_order_status(user, order, status):
    """Notify user about order status changes"""
    payload = {
        'head': f'Order #{order.id} Update',
        'body': f'Your order status has been updated to: {status}',
        'icon': '/static/app/images/logo.png',
        'url': f'/orders/{order.id}/',
    }
    
    send_user_notification(user=user, payload=payload, ttl=1000)

def notify_course_update(enrolled_users, course, update_message):
    """Notify enrolled students about course updates"""
    for user in enrolled_users:
        payload = {
            'head': f'Course Update: {course.title}',
            'body': update_message,
            'icon': course.image.url if hasattr(course, 'image') and course.image else '/static/app/images/logo.png',
            'url': f'/lms/course/{course.id}/',
        }
        
        send_user_notification(user=user, payload=payload, ttl=1000)
