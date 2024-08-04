import os
import json
import hmac
import hashlib
import base64
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
channel_secret = os.getenv('CHANNEL_SECRET')
handler = WebhookHandler(channel_secret)

NLP_SERVICE_URL = "http://nlp-service:5000"
# REMINDER_SERVICE_URL = "http://reminder-service:5000"
USER_DATA_SERVICE_URL = "http://user-data-service:5000"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def get_user_profile(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile.display_name
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return "Unknown User"

def get_user_data(user_id):
    response = requests.get(f"{USER_DATA_SERVICE_URL}/user/{user_id}")
    if response.status_code == 200:
        return response.json()
    else: # If user not found, create a new user with default values
        default_name = get_user_profile(user_id)
        update_user_title(user_id, default_name)
        update_user_timezone(user_id, 'Asia/Taipei')
        return get_user_data(user_id)

    
def update_user_title(user_id, title):
    headers = {'Content-Type': 'application/json'}
    response = requests.put(f"{USER_DATA_SERVICE_URL}/user/{user_id}/title", json={'title': title}, headers=headers)
    return response.json()

def update_user_timezone(user_id, timezone):
    # Retrieve user default title first
    default_name = get_user_profile(user_id)
    headers = {'Content-Type': 'application/json'}
    response = requests.put(f"{USER_DATA_SERVICE_URL}/user/{user_id}/timezone", json={'timezone': timezone, 'title': default_name}, headers=headers)
    return response.json()


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message_text = event.message.text
    headers = {'Content-Type': 'application/json'}

    # Handle users' requests to update their title or timezone
    if message_text.startswith('更改稱呼'):
        new_title = message_text[4:].strip()
        update_user_title(user_id, new_title)
        reply_message(event, f"好的，我記住了！您是 {message_text[2:]}")
        return
    elif message_text.startswith('切換時區'):
        new_timezone = message_text[4:].strip()
        update_user_timezone(user_id, new_timezone)
        reply_message(event, f"好的，我記住了！您的時區是 {message_text[6:]}")
        return
    else:
        # Create requests data for nlp-service
        user_title = get_user_data(user_id).get('title', '')
        user_timezone = get_user_data(user_id).get('timezone', 'Asia/Taipei')

        # Extract time and task using NLP service
        response = requests.post(NLP_SERVICE_URL, json={'string': message_text, 'zone': user_timezone, 'default_subject': user_title}, headers=headers)
        data = response.json()
        subject = data.get('subject', '')
        time_expression = data.get('time_expression', '')
        task = data.get('task', '')

        if task and time_expression and subject:
            # Set reminder using Reminder service
            reminder_data = {
                'user_id': user_id,
                'subject': subject,
                'time_expression': time_expression,
                'task': task
            }
            # requests.post(REMINDER_SERVICE_URL, json=reminder_data, headers=headers)
            reply_message(event, f"我會提醒 {subject} 在 '{time_expression}' '{task}' 噠！")
        else:
            reply_message(event, "我不懂您的意思QAQ")

def reply_message(event, text):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
