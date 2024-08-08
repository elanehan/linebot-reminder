import re
from datetime import datetime, timedelta
import pytz


# dict for chinese time and number
time_dict = {'零': 0, '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
week_dict = {'一': '0', '二': '1', '三': '2', '四': '3', '五': '4', '六': '5', '日': '6', '天': '6'}
am_pm_dict = {'早上': 'am', '上午': 'am', '中午': 'pm', '下午': 'pm', '晚上': 'pm', '凌晨': 'am', '半夜': 'am', 'AM': 'am', 'PM': 'pm'}

date_pattern = r'(\d{1,2})/(\d{1,2})'
hour_min_pattern = [
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(am|pm)?\s*(\d{1,2}):(\d{2})\s*(am|pm)?', 'datetime'),  # 今天下午 3:15
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(\d{1,2})\s*(am|pm)', 'time'),  # 明天 3 pm
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?\s*(\d{1,2})點半', 'mix_half_time'),  # 大後天 3點半
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?\s*(\d{1,2})點((\d{2})分)?', 'mix_time'),  # 後天 3點15分, 3點
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?(am|pm)?([零一二兩三四五六七八九十]+)點半', 'chinese_half_time'),  # 這禮拜二三點半
    (r'((?:這週|這禮拜|這星期|下週|下禮拜|下星期|每週|每個禮拜|每星期)([一二三四五六日天])|今天|明天|後天|大後天)?\s*(am|pm)?\s*([零一二兩三四五六七八九十]+)點\s*(([零一二三四五六七八九十]+)分)?', 'chinese_time'),  # 這週五三點(十五分)
    (r'(\d{1,2})個*(分鐘|小時|天|日)後', 'mix_relative_time'),  # 3小時後
    (r'([零一二兩三四五六七八九十]+)個*(秒|分鐘|小時|天|日)後', 'chinese_relative_time'),  # 三十分鐘後
]

# process day
def process_day(day, weekday, now_weekday):
    addday = 0
    if day == '明天':
        addday = 1
    elif day == '後天':
        addday = 2
    elif day == '大後天':
        addday = 3
    elif day.startswith('這星期') or day.startswith('這週') or day.startswith('這個禮拜'):
        addday = int(week_dict[weekday]) - now_weekday
    elif day.startswith('下星期') or day.startswith('下週') or day.startswith('下個禮拜'):
        if int(week_dict[weekday]) < now_weekday:
            addday = 7 - now_weekday + int(week_dict[weekday])
        else:
            addday = 7 + int(week_dict[weekday]) - now_weekday
    elif day.startswith('每星期') or day.startswith('每週') or day.startswith('每個禮拜'):
        addday = -1
    #print(addday)
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


# Extract subject, RFC3339 Format time, task from string
def parse_text(text, zone='America/New_York'):
    # current time
    time = datetime.now(pytz.timezone(zone))

    time_end_idx = -1 # for task extraction
    rep = False
    week = -1 # for cron expression
    
    for key in am_pm_dict.keys():
        text = text.replace(key, am_pm_dict[key])
    text = text.replace('：', ':')
    date_match = re.search(date_pattern, text)
    if date_match:
        month, dday = date_match.groups()
        time = time.replace(day=int(dday), month=int(month))
        time_end_idx = date_match.end()
    #print(text)
    for pattern, pattern_type in hour_min_pattern:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            #print(groups)
            time_end_idx = max(time_end_idx, match.end())
            if pattern_type == 'datetime':
                day, weekday, c_ap, hour, minute, ap = groups
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                if c_ap == 'am' or ap == 'am':
                    if int(hour) == 12: time = time.replace(hour=0)
                    else: time = time.replace(hour=int(hour))
                elif c_ap == 'pm' or ap == 'pm':
                    if int(hour) == 12: time = time.replace(hour=int(hour))
                    else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                time = time.replace(minute=int(minute))
                time = time.replace(second=0)

            elif pattern_type == 'time':
                day, weekday, hour, ap = groups
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                if ap == 'am':
                    if int(hour) == 12: time = time.replace(hour=0)
                    else: time = time.replace(hour=int(hour))
                elif ap == 'pm':
                    if int(hour) == 12: time = time.replace(hour=int(hour))
                    else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                time = time.replace(minute=0)
                time = time.replace(second=0)
                #print('0')
            elif pattern_type == 'mix_half_time':
                day, weekday, cap, hour = groups
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time = time.replace(hour=0)
                        else: time = time.replace(hour=int(hour))
                    elif cap == 'pm':
                        if int(hour) == 12: time = time.replace(hour=int(hour))
                        else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                time = time.replace(minute=30)
                time = time.replace(second=0)
                #print('2')
            elif pattern_type == 'mix_time':
                day, weekday, cap, hour, is_min, minute = groups
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time = time.replace(hour=0)
                        else: time = time.replace(hour=int(hour))
                    elif cap == 'pm':
                        if int(hour) == 12: time = time.replace(hour=int(hour))
                        else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                if is_min:
                    time = time.replace(minute=int(minute))
                else:
                    time = time.replace(minute=0)
                time = time.replace(second=0)
                #print('1')
            elif pattern_type == 'chinese_half_time':
                day, weekday, cap, hour = groups
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                hour = chinese_to_number(hour)
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time = time.replace(hour=0)
                        else: time = time.replace(hour=int(hour))
                    elif cap == 'pm':
                        if int(hour) == 12: time = time.replace(hour=int(hour))
                        else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                time = time.replace(minute=30)
                time = time.replace(second=0)
            elif pattern_type == 'chinese_time':
                day, weekday, cap, hour, is_min, minute = groups
                print(groups)
                if weekday:
                    if process_day(day, weekday, time.weekday()) > -1:
                        time = time + timedelta(days=process_day(day, weekday, time.weekday()))
                    else:
                        rep = True
                        week = int(week_dict[weekday])+1
                        if week == 7: week = 0
                hour = chinese_to_number(hour)
                if cap == 'am' or cap == 'pm':
                    if cap == 'am':
                        if int(hour) == 12: time = time.replace(hour=0)
                        else: time = time.replace(hour=int(hour))
                    elif cap == 'pm':
                        if int(hour) == 12: time = time.replace(hour=int(hour))
                        else: time = time.replace(hour=int(hour) + 12)
                else: time = time.replace(hour=int(hour))
                if is_min:
                    minute = chinese_to_number(minute)
                    time = time.replace(minute=int(minute))
                else: time = time.replace(minute=0)
                time = time.replace(second=0)
                #print('3')
            elif pattern_type == 'mix_relative_time':
                duration, unit = groups
                duration = int(duration)
                if unit == '小時':
                    time = time + timedelta(hours=duration)
                elif unit == '分鐘':
                    time = time + timedelta(minutes=duration)
                elif unit == '天' or unit == '日':
                    time = time + timedelta(days=duration)
            elif pattern_type == 'chinese_relative_time':
                #print('10')
                duration, unit = groups
                duration = chinese_to_number(duration)
                if unit == '小時':
                    time = time + timedelta(hours=duration)
                elif unit == '分鐘':
                    time = time + timedelta(minutes=duration)
                elif unit == '天' or unit == '日':
                    time = time + timedelta(days=duration)
            
            break
    if rep:
        tt = [' '] * 9
        tt[0] = str(time.minute)
        tt[2] = str(time.hour)
        tt[4] = '*'
        tt[6] = '*'
        tt[8] = str(week)
        time_expression = ''.join(tt)
    else:
        time_expression = ''.join([str(time.minute), ' ', str(time.hour), ' ', str(time.day), ' ', str(time.month), ' ', '*'])

    # extract subject
    subject_match = re.search(r'@[^ ，]+', text)  # Match text starting with "＠" and ending before space/comma
    #print(text)
    #print(subject_match)
    
    if subject_match:
        subject = subject_match.group(0)
        #print(subject)
    else:
        # If no subject is found or subject is "我", use default subject
        subject = '你'

    # extract task
    task = text[time_end_idx:].strip()
    task = re.sub(r'[，,、。！？!?；~～><]+$', '', task)


    if time_end_idx > 0:
        return subject, time_expression, task, rep
    else:
        return None, None, None, rep



#test_strings = '提醒 ＠多芣朗炫34打擊砲 明天下午 4點 幫貓洗澡。'
#test_strings = '我 這禮拜天早上十點三十五分 跟朋友有約 ~'
#test_strings = '我這星期一半夜兩點半 要睡覺 ~'
#test_strings = '提醒我 每週五 3:15am 幫hona洗澡。'
#test_strings = '提醒我 6/22 3:15pm 打掃。'
#test_strings = '提醒我 40分鐘後 關瓦斯'
#test_strings = '提醒我 二十小時後 撿五個垃圾'
#test_strings = '提醒我 二十天後 收包裹'
#test_strings = '提醒我 每週二 4PM 運動'




# subject, time, task, rep = parse_text(test_strings)
# print(f"{test_strings} -> {subject} {time} {task}")