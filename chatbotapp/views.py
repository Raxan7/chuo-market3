from django.shortcuts import redirect, render
from Commerce.settings import GENERATIVE_AI_KEY
from chatbotapp.models import ChatMessage, UnauthenticatedChatMessage
import google.generativeai as genai
from django.http import JsonResponse
import json
import asyncio
from asgiref.sync import sync_to_async

async def send_message(request):
    if request.method == 'POST':
        genai.configure(api_key=GENERATIVE_AI_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        user_message = request.POST.get('user_message')
        
        # Modify the user message to include the context and instructions
        prompt = f"""
        You are the AI Lecturer Assistant for the ChuoSmart App, designed by the team at ChuoSmart to aid users with any questions they have. 
        You are not developed by Google, and you are not Gemini. 
        You are an LLM (Large Language Model) ready to assist with anything university-related and more. 
        Your tagline is: "Ready to assist you."
        
        User: {user_message}
        AI Lecturer Assistant:
        """
        
        # Generate the bot's response using the modified prompt
        bot_response = await asyncio.to_thread(model.generate_content, prompt)

        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        if is_authenticated:
            await sync_to_async(ChatMessage.objects.create)(
                user_message=user_message,
                bot_response=bot_response.text,
                user=request.user
            )
        else:
            session_key = request.session.session_key
            await sync_to_async(UnauthenticatedChatMessage.objects.create)(
                user_message=user_message,
                bot_response=bot_response.text,
                session_key=session_key
            )
            if 'messages' not in request.session:
                request.session['messages'] = []
            request.session['messages'].append({
                'user_message': user_message,
                'bot_response': bot_response.text
            })
            request.session.modified = True

    return redirect('home')

async def list_messages(request):
    is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
    if is_authenticated:
        messages = await sync_to_async(list)(ChatMessage.objects.filter(user=request.user))
    else:
        messages = request.session.get('messages', [])
    return render(request, 'chatbotapp/list_messages.html', { 'messages': messages })

def chatbot_api(request):
    if request.method == 'POST':
        genai.configure(api_key=GENERATIVE_AI_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        data = json.loads(request.body)
        user_message = data.get('message')
        bot_response = model.generate_content(user_message)

        if request.user.is_authenticated:
            ChatMessage.objects.create(
                user_message=user_message,
                bot_response=bot_response.text,
                user=request.user
            )
        else:
            UnauthenticatedChatMessage.objects.create(
                user_message=user_message,
                bot_response=bot_response.text
            )
            if 'messages' not in request.session:
                request.session['messages'] = []
            request.session['messages'].append({
                'user_message': user_message,
                'bot_response': bot_response.text
            })
            request.session.modified = True

        return JsonResponse({'reply': bot_response.text})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def clear_session(request):
    time.sleep(5)
    request.session.flush()
    return JsonResponse({'status': 'Session cleared'})