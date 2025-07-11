# Push Notification System for ChuoSmart

This document provides information about using the push notification system in ChuoSmart.

## Overview

ChuoSmart now supports web push notifications, allowing you to send real-time alerts to users' browsers even when they're not actively using the site. This feature uses the Web Push API and service workers.

## How It Works

1. Users are prompted to allow notifications when they visit the site
2. If they accept, their browser will receive push notifications even when the site is closed
3. Notifications can be triggered by various events in the system

## How to Send Notifications

### From Views

You can send notifications from your views using the utility functions in `core/notifications.py`:

```python
from core.notifications import notify_new_product, notify_new_message, notify_order_status, notify_course_update

# Example: Send notification when a new product is created
def create_product(request):
    # ... product creation code ...
    if product.is_published:
        notify_new_product(request.user, product)
    
    return redirect('product-detail', product.id)
```

### Direct API

You can also use the direct API endpoints:

- `/notifications/test/` - Send a test notification to the current user
- `/notifications/send/` - Send a notification to the current user
- `/notifications/send/<user_id>/` - Send a notification to a specific user
- `/notifications/group/<group_name>/` - Send a notification to all users in a group

### Common Use Cases

Here are recommended places to add notifications in the ChuoSmart system:

1. **New Messages**: When a user receives a new private message
2. **Order Status Updates**: When an order's status changes
3. **New Products**: When a followed seller lists a new product
4. **Course Updates**: When a course is updated or new materials are added
5. **Promotions and Discounts**: For special offers or time-limited deals

## Notification Payload Structure

When sending notifications, you need to provide a payload with the following structure:

```python
payload = {
    'head': 'Notification Title',
    'body': 'Notification message text',
    'icon': '/path/to/icon.png',  # URL to an icon image
    'url': '/path/to/redirect',   # URL to redirect when notification is clicked
}
```

## Implementation Details

The notification system is implemented using:

- `django-webpush` for server-side push notification handling
- A service worker (`service-worker.js`) for client-side notification display
- VAPID keys for secure communication

## Troubleshooting

1. **Notifications not showing**: Make sure the user has granted notification permission
2. **Service worker errors**: Check browser console for errors
3. **Push subscription issues**: Ensure VAPID keys are correctly configured

## Future Improvements

- Add notification preferences in user settings
- Implement notification grouping and categories
- Add support for rich notifications with images and action buttons
