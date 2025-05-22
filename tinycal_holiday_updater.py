import json
import plistlib
import os
import re
import requests # For fetching data from URL
import shutil # For file backup
from datetime import datetime

# --- Configuration ---
CALENDAR_DIR = os.path.join(os.path.expanduser("~"), "Library/Containers/app.cyan.tinycalx/Data/Documents/calendars")
HOLIDAY_JSON_URL_TEMPLATE = "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json"
BACKUP_DIR = os.path.join(os.getcwd(), "backup") 

def fetch_holiday_data(year):
    """
    从指定的 URL 下载并解析指定年份的节假日 JSON 数据。

    Args:
        year (int): 需要获取数据的年份。

    Returns:
        dict: 包含节假日安排的字典 (schedule_map)，如果失败则返回 None。
    """
    url = HOLIDAY_JSON_URL_TEMPLATE.format(year=year)
    print(f"正在从 {url} 获取 {year} 年的节假日数据...")
    try:
        response = requests.get(url, timeout=10) # 10秒超时
        response.raise_for_status()  # 如果 HTTP 请求返回了不成功的状态码，则抛出 HTTPError 异常
        holiday_data = response.json()

        schedule_map = {}
        if 'days' in holiday_data and isinstance(holiday_data['days'], list):
            for day_info in holiday_data['days']:
                if 'date' in day_info and 'isOffDay' in day_info:
                    schedule_map[day_info['date']] = day_info['isOffDay']
                else:
                    print(f"警告：跳过 JSON 中的无效条目: {day_info}")
            if not schedule_map:
                print(f"警告：从 {year} 年的 JSON 数据中未能解析出任何日期安排。")
                return None
            print(f"成功获取并解析 {year} 年的节假日数据。")
            return schedule_map
        else:
            print(f"错误：{year} 年的 JSON 文件格式不正确，缺少 'days' 列表。")
            return None
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"错误：未找到 {year} 年的节假日数据 (404 Not Found)。请检查年份是否正确或该年份数据是否存在。")
        else:
            print(f"HTTP 错误： {http_err} - 无法获取 {year} 年的节假日数据。")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误： {req_err} - 无法连接到服务器获取 {year} 年的节假日数据。")
        return None
    except json.JSONDecodeError:
        print(f"错误：无法解码从 {url} 获取的 JSON 数据。")
        return None
    except Exception as e:
        print(f"获取或解析 {year} 年节假日数据时发生未知错误: {e}")
        return None

def update_single_plist_file(plist_file_path, year_schedule_map):
    """
    备份并根据提供的节假日安排更新单个 PList 日历文件中的 worktime 键。
    此函数会直接修改文件。

    Args:
        plist_file_path (str): PList 日历文件的完整路径。
        year_schedule_map (dict): 包含该年份节假日/工作日安排的字典。

    Returns:
        tuple: (bool, bool) 第一个 bool 表示文件是否被修改，第二个 bool 表示操作是否成功。
    """
    # --- Backup original file ---
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"已创建备份目录: {BACKUP_DIR}")

        base_filename = os.path.basename(plist_file_path)
        backup_file_path = os.path.join(BACKUP_DIR, base_filename)
        
        # 检查原文件是否存在，防止shutil.copy2报错
        if not os.path.exists(plist_file_path):
            print(f"错误：原文件 {plist_file_path} 不存在，无法备份和更新。")
            return False, False

        shutil.copy2(plist_file_path, backup_file_path)
        print(f"已将原文件 {base_filename} 备份到 {backup_file_path}")
    except Exception as backup_err:
        print(f"错误：备份文件 {plist_file_path} 失败: {backup_err}")
        # 根据策略，可以选择在此处返回失败，或者继续尝试更新文件
        # 当前策略：备份失败也尝试更新，但给予警告
        # return False, False # 如果希望备份失败则不进行更新，取消此行注释

    # --- Load and update PList file ---
    try:
        with open(plist_file_path, 'rb') as fp:
            plist_content = plistlib.load(fp)
    except FileNotFoundError: # 理论上已通过上面的检查，但作为双重保障
        print(f"错误：未找到 PList 文件 {plist_file_path} (在尝试读取时)")
        return False, False
    except plistlib.InvalidFileException:
        print(f"错误：PList 文件格式无效 {plist_file_path}")
        return False, False
    except Exception as e:
        print(f"读取 PList 文件 {plist_file_path} 时发生未知错误: {e}")
        return False, False

    if 'monthData' not in plist_content or not isinstance(plist_content['monthData'], list):
        print(f"错误：PList 文件 {plist_file_path} 中缺少 'monthData' 或其值不是列表。")
        return False, False

    updated_entries_count = 0
    modified_in_this_file = False

    for item in plist_content['monthData']:
        if not all(k in item for k in ['year', 'month', 'day']):
            continue

        try:
            item_year = int(item['year'])
            item_month = int(item['month'])
            item_day = int(item['day'])
            current_date_str = f"{item_year:04d}-{item_month:02d}-{item_day:02d}"
        except ValueError:
            continue

        if current_date_str in year_schedule_map:
            is_off_day = year_schedule_map[current_date_str]
            new_worktime = 2 if is_off_day else 1
            
            if item.get('worktime') != new_worktime:
                item['worktime'] = new_worktime
                updated_entries_count += 1
                modified_in_this_file = True

    if modified_in_this_file:
        try:
            with open(plist_file_path, 'wb') as fp:
                plistlib.dump(plist_content, fp)
            print(f"文件 {os.path.basename(plist_file_path)} 已成功更新。共修改 {updated_entries_count} 个日期的状态。")
            return True, True
        except Exception as e:
            print(f"错误：保存更新后的 PList 文件 {plist_file_path} 时出错: {e}")
            return True, False # 尝试修改但保存失败
    elif updated_entries_count == 0 and not modified_in_this_file:
        # print(f"文件 {os.path.basename(plist_file_path)} 无需更新 (未找到匹配日期或状态已正确)。")
        return False, True
    else:
        print(f"文件 {os.path.basename(plist_file_path)} 中的日期状态已是最新，无需更新。")
        return False, True


def main():
    """
    主函数，处理用户交互和文件处理流程。
    """
    print("TinyCal 日历节假日更新脚本")
    print("-----------------------------")
    print(f"日历配置目录: {CALENDAR_DIR}")
    print(f"备份文件将保存到: {BACKUP_DIR}")
    print("-----------------------------")
    print("请选择操作：")
    print("1. 更新今年 (" + str(datetime.now().year) + ") 的日历")
    print("2. 输入特定年份进行更新")

    choice = input("请输入选项 (1 或 2): ")
    target_year = 0

    if choice == '1':
        target_year = datetime.now().year
    elif choice == '2':
        while True:
            try:
                year_input = input("请输入4位数的年份 (例如 2025): ")
                target_year = int(year_input)
                if 1800 < target_year < 2200:
                    break
                else:
                    print("请输入一个有效的年份。")
            except ValueError:
                print("输入无效，请输入数字年份。")
    else:
        print("无效选项。退出脚本。")
        return

    print(f"\n准备更新 {target_year} 年的日历文件...")

    year_schedule_map = fetch_holiday_data(target_year)
    if not year_schedule_map:
        print(f"未能获取 {target_year} 年的节假日数据。无法继续。")
        return

    if not os.path.isdir(CALENDAR_DIR):
        print(f"错误：日历目录 '{CALENDAR_DIR}' 不存在。")
        print("请确认该路径是正确的，并且您有权限访问它。")
        return
    
    print(f"\n将在目录 '{CALENDAR_DIR}' 中查找并处理 {target_year} 年的日历文件...")

    total_files_processed = 0
    files_actually_updated = 0
    files_failed_to_update = 0
    
    filename_pattern = re.compile(r"(\d{4})\.(\d{1,2})\.0 \(zh_CN\)")

    for filename in os.listdir(CALENDAR_DIR):
        match = filename_pattern.fullmatch(filename)
        if match:
            file_year_str = match.group(1)
            try:
                file_year = int(file_year_str)
                if file_year == target_year:
                    total_files_processed +=1
                    plist_file_full_path = os.path.join(CALENDAR_DIR, filename)
                    
                    print(f"\n--- 正在处理文件: {filename} ---")
                    modified_status, success_status = update_single_plist_file(plist_file_full_path, year_schedule_map)
                    
                    if modified_status and success_status:
                        files_actually_updated += 1
                    elif not success_status:
                        files_failed_to_update +=1
            except ValueError:
                print(f"警告：文件名 {filename} 中的年份格式不正确，跳过。")
                continue
    
    print("\n-----------------------------")
    print("脚本执行完毕。")
    if total_files_processed == 0:
        print(f"在目录 '{CALENDAR_DIR}' 中没有找到属于 {target_year} 年的日历文件。")
    else:
        print(f"共检查 {total_files_processed} 个 {target_year} 年的日历文件。")
        print(f"其中 {files_actually_updated} 个文件被成功更新并已备份。")
        if files_failed_to_update > 0:
            print(f"注意：有 {files_failed_to_update} 个文件在尝试更新时发生错误 (即使已备份)。请检查上面的日志。")
        
        # 计算无需更新的文件数，这些文件可能已备份但内容未更改
        files_no_change_needed = total_files_processed - files_actually_updated - files_failed_to_update
        if files_no_change_needed > 0:
             print(f"{files_no_change_needed} 个文件无需更新（已是最新或无匹配日期），但仍执行了备份。")
    print(f"所有备份文件（如有）均保存在: {BACKUP_DIR}")
    print("-----------------------------")

if __name__ == "__main__":
    main()
