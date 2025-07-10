from django.urls import path
from .views import send_message, list_messages, chatbot_api

urlpatterns = [
    path('send/', send_message, name='send_message'),
    path('', list_messages, name='list_messages'),
    path('chatbot/', chatbot_api, name='chatbot_api'),
]