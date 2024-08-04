import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
def get_user_data(sheet, user_id):
    data = sheet.get_all_records()
    for row in data:
        if row['user_id'] == user_id:
            return row
    return None

# Function to update user's title
def update_user_title(sheet, user_id, title=None):
    data = sheet.get_all_records()
    row_index = 2  # Starting from 2 because get_all_records() skips the header
    for row in data:
        if row['user_id'] == user_id:
            if title:
                sheet.update_cell(row_index, 2, title)  # Update title
            return
        row_index += 1
    
    # If user_id not found, append a new row
    new_row = [user_id, title, 'Asia/Taipei']
    sheet.append_row(new_row)

# Function to update user's timezone
def update_user_timezone(sheet, user_id, timezone=None):
    timezone_dict = {"台灣": "Asia/Taipei", "美東": "America/New_York", "美西": "America/Los_Angeles", "日本": "Asia/Tokyo"}
    data = sheet.get_all_records()
    row_index = 2  # Starting from 2 because get_all_records() skips the header
    for row in data:
        if row['user_id'] == user_id:
            if timezone:
                timezone = timezone_dict.get(timezone, timezone)
                sheet.update_cell(row_index, 3, timezone)  # Update timezone
            return
        row_index += 1
    
    # If user_id not found, append a new row
    timezone = timezone_dict.get(timezone, timezone)
    new_row = [user_id, '你', timezone]
    sheet.append_row(new_row)

# Example usage within this module (for testing)
if __name__ == "__main__":
    client = get_gspread_client()
    sheet = get_sheet(client)
    user_id = "U1234567890"
    title = "Babe"
    timezone = "日本"
    
    # Get user data
    user_data = get_user_data(sheet, user_id)
    print(user_data)
    
    # Update user data
    update_user_title(sheet, user_id, title)
    update_user_timezone(sheet, user_id, timezone)
