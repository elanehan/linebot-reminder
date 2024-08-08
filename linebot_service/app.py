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
REMINDER_SERVICE_URL = "http://reminder-service:5000"
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

def create_scheduler_job(timezone, user_id, time_expression, subject, task, rep):
    headers = {'Content-Type': 'application/json'}
    data = {
        'timezone': timezone,
        'user_id': user_id,
        'time_expression': time_expression,
        'subject': subject,
        'task': task,
        'rep': rep
    }
    response = requests.post(f"{REMINDER_SERVICE_URL}/reminder", json=data, headers=headers)
    return response.json()

def delete_scheduler_job(timezone, user_id, time_expression):
    headers = {'Content-Type': 'application/json'}
    data = {
        'timezone': timezone,
        'user_id': user_id,
        'time_expression': time_expression
    }
    response = requests.delete(f"{REMINDER_SERVICE_URL}/reminder", json=data, headers=headers)
    return response.json()

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event['source']['userId']
    message_text = event['message']['text']

    source_type = event['source']['type']
    #print(f"Source type: {source_type}")


    # Handle users' requests to update their title or timezone
    if message_text.startswith('更改稱呼'):
        new_title = message_text[4:].strip()
        update_user_title(user_id, new_title)
        reply_message(event, f"好的，我記住了！我會稱呼您為 {new_title}")
    elif message_text.startswith('切換時區'):
        new_timezone = message_text[4:].strip()
        update_user_timezone(user_id, new_timezone)
        reply_message(event, f"好的，我記住了！您的時區是 {new_timezone}")
    elif message_text.startswith('取消'): # Cancel reminder of a time
        # Create requests data for nlp-service
        default_name = get_user_profile(user_id)
        user_title, user_timezone = get_user_data(user_id, default_name)

        # Extract time using NLP service
        subject, time_expression, task, rep = parse_text(message_text, user_timezone, user_title)

        if time_expression:
            # Delete reminder using Reminder service
            reply_message(event, f"好的，此項提醒已取消。")
            delete_scheduler_job(user_timezone, user_id, time_expression)
        else:
            reply_message(event, "我不懂您的意思QAQ")

    else:
        # Create requests data for nlp-service
        default_name = get_user_profile(user_id)
        user_title, user_timezone = get_user_data(user_id, default_name)
        if source_type == 'group':
            if message_text.startswith('提醒'):
                subject, time_expression, task, rep = parse_text(message_text, user_timezone)
                if task and time_expression and subject:
                    reply_message(event, f"我會記得提醒 {subject} {task} 噠！")
                    group_id = event['source']['groupId']
                    create_scheduler_job(user_timezone, group_id, time_expression, subject, task, rep)  
        else:
            # Extract time and task using NLP service
            subject, time_expression, task, rep = parse_text(message_text, user_timezone)
            # print(f"Subject: {subject}, Time: {time_expression}, Task: {task}")

            if task and time_expression and subject:
                # Set reminder using Reminder service
                reply_message(event, f"我會記得提醒 {user_title} {task} 噠！")
                create_scheduler_job(user_timezone, user_id, time_expression, user_title, task, rep)
            else:
                reply_message(event, "我不懂您的意思QAQ")

def reply_message(event, text):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
