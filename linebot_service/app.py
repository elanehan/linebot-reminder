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

NLP_SERVICE_URL = os.getenv('NLP_SERVICE_URL')
REMINDER_SERVICE_URL = os.getenv('REMINDER_SERVICE_URL')
USER_DATA_SERVICE_URL = os.getenv('USER_DATA_SERVICE_URL')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message_text = event.message.text
    headers = {'Content-Type': 'application/json'}
    
    # Extract entities using NLP service
    response = requests.post(NLP_SERVICE_URL, json={'text': message_text}, headers=headers)
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
        requests.post(REMINDER_SERVICE_URL, json=reminder_data, headers=headers)
        reply_message(event, f"我會提醒 {subject} 在 '{time_expression}' '{task}' 噠！")
    else:
        reply_message(event, "我不懂您的意思QAQ")

def reply_message(event, text):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

if __name__ == '__main__':
    app.run(debug=True)
