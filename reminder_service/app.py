import os
from flask import Flask, request
from linebot import LineBotApi
from linebot.models import TextSendMessage
from google.cloud import scheduler_v1

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
client = scheduler_v1.CloudSchedulerClient()

@app.route("/", methods=['POST'])
def send_reminder():
    request_data = request.get_json()
    user_id = request_data.get('user_id')
    user_title = request_data.get('title')
    task = request_data.get('task')
    rep = request_data.get('rep')
    job_name = request_data.get('job_name')

    if user_id and user_title and task:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"{user_title} 到{task}的時間囉！"))
    if rep == False:
        client.delete_job(name=job_name)
    
    return 'OK', 200
    

if __name__ == "__main__":
    app.run(debug=True)
