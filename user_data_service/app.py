import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load the service account credentials
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name('../data/linebot-reminder-431422-caacdd8a7834.json', scope)
    client = gspread.authorize(credentials)
    return client

# Open the Google Sheet by its name
def get_sheet(client, sheet_name="Linebot"):
    return client.open(sheet_name).sheet1

# Function to get user data
@app.route('/user/<user_id>', methods=['GET'])
def get_user_data(user_id):
    client = get_gspread_client()
    sheet = get_sheet(client)
    data = sheet.get_all_records()
    for row in data:
        if row['user_id'] == user_id:
            return jsonify(row)
    return jsonify({'message': 'User not found'}), 404

# Function to update user's title
@app.route('/user/<user_id>/title', methods=['PUT'])
def update_user_title(user_id, title=None):
    client = get_gspread_client()
    sheet = get_sheet(client)
    data = sheet.get_all_records()
    row_index = 2  # Starting from 2 because get_all_records() skips the header
    for row in data:
        if row['user_id'] == user_id:
            if title:
                sheet.update_cell(row_index, 2, title)  # Update title
            return jsonify({'message': 'User found, title updated'}), 200
        row_index += 1
    
    # If user_id not found, append a new row
    new_row = [user_id, title, 'Asia/Taipei']
    sheet.append_row(new_row)
    return jsonify({'message': 'User not found, new row added'}), 201

# Function to update user's timezone
@app.route('/user/<user_id>/timezone', methods=['PUT'])
def update_user_timezone(user_id, timezone=None, title=None):
    client = get_gspread_client()
    sheet = get_sheet(client)
    timezone_dict = {"台灣": "Asia/Taipei", "美東": "America/New_York", "美西": "America/Los_Angeles", "日本": "Asia/Tokyo"}
    data = sheet.get_all_records()
    row_index = 2  # Starting from 2 because get_all_records() skips the header
    for row in data:
        if row['user_id'] == user_id:
            if timezone:
                timezone = timezone_dict.get(timezone, timezone)
                sheet.update_cell(row_index, 3, timezone)  # Update timezone
            return jsonify({'message': 'User found, timezone updated'}), 200
        row_index += 1
    
    # If user_id not found, append a new row
    timezone = timezone_dict.get(timezone, timezone)
    new_row = [user_id, title, timezone]
    sheet.append_row(new_row)
    return jsonify({'message': 'User not found, new row added'}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
