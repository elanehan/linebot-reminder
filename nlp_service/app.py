from flask import Flask, request, jsonify
import re
from datetime import datetime
import pytz

app = Flask(__name__)

# dict for chinese time and number
time_dict = {'零': 0, '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
week_dict = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '日': '7', '天': '7'}
am_pm_dict = {'早上': 'am', '上午': 'am', '中午': 'pm', '下午': 'pm', '晚上': 'pm', '凌晨': 'am', '半夜': 'am', 'AM': 'am', 'PM': 'pm'}

date_pattern = r'(\d{1,2})/(\d{1,2})'
hour_min_pattern = [
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(am|pm)?\s*(\d{1,2}):(\d{2})\s*(am|pm)?', 'datetime'),  # 今天下午 3:15
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(\d{1,2})\s*(am|pm)', 'time'),  # 明天 3 pm
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?\s*(\d{1,2})點半', 'mix_half_time'),  # 大後天 3點半
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?\s*(\d{1,2})點((\d{2})分)?', 'mix_time'),  # 後天 3點15分, 3點
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?([零一二兩三四五六七八九十]+)點半', 'chinese_half_time'),  # 這禮拜二三點半
    (r'(這(?:週|禮拜|星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(am|pm)?\s*([零一二兩三四五六七八九十]+)點\s*(([零一二三四五六七八九十]+)分)?', 'chinese_time'),  # 這週五三點(十五分)
    (r'(\d{1,2})(分鐘|小時|天|日)後', 'mix_relative_time'),  # 3小時後
    (r'([零一二兩三四五六七八九十]+)(分鐘|小時|天|日)後', 'chinese_relative_time'),  # 三十分鐘後
]

# process day
def process_day(day):
    addday = 0
    if day == '明天':
        addday = 1
    elif day == '後天':
        addday = 2
    elif day == '大後天':
        addday = 3
    return addday

def chinese_to_number(chinese_time):
    number = 0
    for char in chinese_time:
        if char == '十' and number == 0:
            number = 10
        elif char == '十':
            number *= 10
        else:
            number += time_dict[char]
    return number

def time_overflow_check(minute, hour, day, month):
    minute, hour = int(minute), int(hour)
    if day != '*' and month != '*':
        day, month = int(day), int(month)
        if minute >= 60: # minute -> hour
            add_hour = minute // 60
            minute = minute % 60
            hour = hour + add_hour
        if hour >= 24: # hour -> day
            add_day = hour // 24
            hour = hour % 24
            day = day + add_day
        # day -> month
        while True:
            if month in [1, 3, 5, 7, 8, 10, 12] and day > 31:
                day -= 31
                month += 1
            elif month in [4, 6, 9, 11] and day > 30:
                day -= 30
                month += 1
            elif month == 2 and day > 28:
                day -= 28
                month += 1
            else:
                break

            if month > 12:
                month -= 12
    # if 下週 or 星期 was used, then i will assume minute and hour will not be over 60 and 24
    return str(minute), str(hour), str(day), str(month)


# extract subject, time and task from string
def parse_text(text, zone='Asia/Taipei', default_subject='我'):
    # current time
    now = datetime.now(pytz.timezone(zone))

    # time expression array for cron
    time_expression = [' '] * 9
    time_expression[0] = str(now.minute)
    time_expression[2] = str(now.hour)
    time_expression[4] = str(now.day)
    time_expression[6] = str(now.month)
    time_expression[8] = '*'
    #print(''.join(time_expression))
    time_end_idx = 0
    
    for key in am_pm_dict.keys():
        text = text.replace(key, am_pm_dict[key])
    date_match = re.search(date_pattern, text)
    if date_match:
        day, month = date_match.groups()
        time_expression[4] = day
        time_expression[6] = month
        time_end_idx = date_match.end()
    #print(text)
    for pattern, pattern_type in hour_min_pattern:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            time_end_idx = max(time_end_idx, match.end())
            if pattern_type == 'datetime':
                print(groups)
                day, weekday, c_ap, hour, minute, ap = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                if c_ap == 'am' or ap == 'am':
                    if int(hour) == 12: time_expression[2] = '0'
                    else: time_expression[2] = hour
                elif c_ap == 'pm' or ap == 'pm':
                    if int(hour) == 12: time_expression[2] = hour
                    else: time_expression[2] = str(int(hour) + 12)
                else: time_expression[2] = hour
                time_expression[0] = minute
            elif pattern_type == 'time':
                day, weekday, hour, ap = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                if ap == 'am':
                    if int(hour) == 12: time_expression[2] = '0'
                    else: time_expression[2] = hour
                elif ap == 'pm':
                    if int(hour) == 12: time_expression[2] = hour
                    else: time_expression[2] = str(int(hour) + 12)
                else: time_expression[2] = hour
                time_expression[0] = '0'
                #print('0')
            elif pattern_type == 'mix_half_time':
                day, weekday, cap, hour = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time_expression[2] = '0'
                        else: time_expression[2] = hour
                    elif cap == 'pm':
                        if int(hour) == 12: time_expression[2] = hour
                        else: time_expression[2] = str(int(hour) + 12)
                else: time_expression[2] = hour
                time_expression[0] = '30'
                #print('2')
            elif pattern_type == 'mix_time':
                day, weekday, cap, hour, is_min, minute = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time_expression[2] = '0'
                        else: time_expression[2] = hour
                    elif cap == 'pm':
                        if int(hour) == 12: time_expression[2] = hour
                        else: time_expression[2] = str(int(hour) + 12)
                else: time_expression[2] = hour
                if is_min:
                    time_expression[0] = minute
                else:
                    time_expression[0] = '0'
                #print('1')
            elif pattern_type == 'chinese_half_time':
                day, weekday, cap, hour = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                hour = chinese_to_number(hour)
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if hour == 12: time_expression[2] = '0'
                        else: time_expression[2] = str(hour)
                    elif cap == 'pm':
                        if hour == 12: time_expression[2] = str(hour)
                        else: time_expression[2] = str(hour + 12)
                else: time_expression[2] = str(hour)
                time_expression[0] = '30'
            elif pattern_type == 'chinese_time':
                day, weekday, cap, hour, is_min, minute = groups
                if weekday:
                    time_expression[8] = week_dict[weekday]
                    time_expression[4] = '*'
                    time_expression[6] = '*'
                else:
                    time_expression[4] = str(int(time_expression[4]) + process_day(day))
                hour = chinese_to_number(hour)
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if hour == 12: time_expression[2] = '0'
                        else: time_expression[2] = str(hour)
                    elif cap == 'pm':
                        if hour == 12: time_expression[2] = str(hour)
                        else: time_expression[2] = str(hour + 12)
                else: time_expression[2] = str(hour)
                if is_min:
                    minute = chinese_to_number(minute)
                    time_expression[0] = str(minute)
                else: time_expression[0] = '0'
                #print('3')
            elif pattern_type == 'mix_relative_time':
                duration, unit = groups
                duration = int(duration)
                if unit == '小時':
                    time_expression[2] = str(int(time_expression[2]) + duration)
                elif unit == '分鐘':
                    time_expression[0] = str(int(time_expression[0]) + duration)
                elif unit == '天' or unit == '日':
                    time_expression[4] = str(int(time_expression[4]) + duration)
            elif pattern_type == 'chinese_relative_time':
                #print('10')
                duration, unit = groups
                duration = chinese_to_number(duration)
                if unit == '小時':
                    time_expression[2] = str(int(time_expression[2]) + duration)
                elif unit == '分鐘':
                    time_expression[0] = str(int(time_expression[0]) + duration)
                elif unit == '天' or unit == '日':
                    time_expression[4] = str(int(time_expression[4]) + duration)

            # time overflow check
            mi, hr, dd, mo = time_overflow_check(time_expression[0], time_expression[2], time_expression[4], time_expression[6])
            time_expression[0], time_expression[2], time_expression[4], time_expression[6] = mi, hr, dd, mo
            
            break
    tt = ''.join(time_expression)

    # extract task
    task = text[time_end_idx:].strip()
    task = re.sub(r'[，,、。！？!?；~～><]+$', '', task)

    # extract subject
    subject_match = re.search(r'＠[^ ，]+', text)  # Match text starting with "＠" and ending before space/comma
    if subject_match:
        subject = subject_match.group(0)
    else:
        # If no subject is found or subject is "我", use default subject
        subject = default_subject

    if time_end_idx > 0:
        return subject, tt, task 
    else:
        return None, None, None

@app.route('/nlp_service', methods=['POST'])
def nlp_service():
    data = request.json
    string = data.get('string', '')
    zone = data.get('zone', 'Asia/Taipei')
    default_subject = data.get('default_subject', '我')
    subj, cron_expression, task = parse_text(string, zone, default_subject)
    if cron_expression == ' ':
        return jsonify({'error': 'No time expression found'})
    return jsonify({'subject': subj, 'time_expressions': cron_expression, 'task': task})

if __name__ == '__main__':
    app.run(debug=True)