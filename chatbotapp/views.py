from django.shortcuts import redirect, render
from Commerce.settings import CEREBRAS_API_KEY
from chatbotapp.models import ChatMessage, UnauthenticatedChatMessage
from cerebras.cloud.sdk import Cerebras
from django.http import JsonResponse
import json
import asyncio
import time
from asgiref.sync import sync_to_async

from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync

@require_http_methods(["GET", "POST"])
def send_message(request):
    """
    Handle sending messages to the chatbot.
    We're using sync version of the function for better compatibility with Django's form handling.
    """
    if request.method == 'POST':
        client = Cerebras(api_key=CEREBRAS_API_KEY)

        user_message = request.POST.get('user_message')
        
        # Modify the user message to include the context and instructions
        system_prompt = """You are the AI Lecturer Assistant for the ChuoSmart App, designed by the team at ChuoSmart to aid users with any questions they have. 
        You are powered by Cerebras AI with ultra-fast inference.
        You are an LLM (Large Language Model) ready to assist with anything university-related and more. 
        Your tagline is: "Ready to assist you."""
        
        # Generate the bot's response using Cerebras API
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1024,
                top_p=1
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            response_text = f"Sorry, I couldn't process that request: {str(e)}"
        
        if request.user.is_authenticated:
            ChatMessage.objects.create(
                user_message=user_message,
                bot_response=response_text,
                user=request.user
            )
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
                
            UnauthenticatedChatMessage.objects.create(
                user_message=user_message,
                bot_response=response_text,
                session_key=session_key
            )
            
            if 'messages' not in request.session:
                request.session['messages'] = []
            
            request.session['messages'].append({
                'user_message': user_message,
                'bot_response': response_text
            })
            request.session.modified = True

    return redirect('home')

def list_messages(request):
    if request.user.is_authenticated:
        messages = list(ChatMessage.objects.filter(user=request.user))
    else:
        messages = request.session.get('messages', [])
    return render(request, 'chatbotapp/list_messages.html', { 'messages': messages })

def chatbot_api(request):
    if request.method == 'POST':
        client = Cerebras(api_key=CEREBRAS_API_KEY)

        data = json.loads(request.body)
        user_message = data.get('message')
        
        system_prompt = """You are the AI Lecturer Assistant for the ChuoSmart App, designed by the team at ChuoSmart to aid users with any questions they have. 
        You are powered by Cerebras AI with ultra-fast inference.
        You are an LLM (Large Language Model) ready to assist with anything university-related and more. 
        Your tagline is: "Ready to assist you."""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1
        )
        bot_response_text = response.choices[0].message.content

        if request.user.is_authenticated:
            ChatMessage.objects.create(
                user_message=user_message,
                bot_response=bot_response_text,
                user=request.user
            )
        else:
            UnauthenticatedChatMessage.objects.create(
                user_message=user_message,
                bot_response=bot_response_text
            )
            if 'messages' not in request.session:
                request.session['messages'] = []
            request.session['messages'].append({
                'user_message': user_message,
                'bot_response': bot_response_text
            })
            request.session.modified = True

        return JsonResponse({'reply': bot_response_text})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def clear_session(request):
    time.sleep(5)
    request.session.flush()
    return JsonResponse({'status': 'Session cleared'})