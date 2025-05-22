import json
import plistlib
import os
import re
import requests # For fetching data from URL
from datetime import datetime

# --- Configuration ---
CALENDAR_DIR = os.path.join(os.path.expanduser("~"), "Library/Containers/app.cyan.tinycalx/Data/Documents/calendars")
HOLIDAY_JSON_URL_TEMPLATE = "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json"

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
    根据提供的节假日安排更新单个 PList 日历文件中的 worktime 键。
    此函数会直接修改文件。

    Args:
        plist_file_path (str): PList 日历文件的完整路径。
        year_schedule_map (dict): 包含该年份节假日/工作日安排的字典。

    Returns:
        tuple: (bool, bool) 第一个 bool 表示文件是否被修改，第二个 bool 表示操作是否成功。
               例如 (True, True) 表示文件被修改且操作成功。
               (False, True) 表示文件未被修改（因为无需更新或未找到匹配日期）但操作逻辑成功。
               (False, False) 表示操作失败。
    """
    try:
        with open(plist_file_path, 'rb') as fp:
            plist_content = plistlib.load(fp)
    except FileNotFoundError:
        print(f"错误：未找到 PList 文件 {plist_file_path}")
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

    updated_entries_count = 0 # 记录此文件中实际更新的条目数
    modified_in_this_file = False # 标记此文件是否实际被修改

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
            print(f"文件 {os.path.basename(plist_file_path)} 已更新。共修改 {updated_entries_count} 个日期的状态。")
            return True, True # 文件被修改，操作成功
        except Exception as e:
            print(f"错误：保存更新后的 PList 文件 {plist_file_path} 时出错: {e}")
            return True, False # 文件尝试修改，但保存失败
    elif updated_entries_count == 0 and not modified_in_this_file: # 没有条目被更新，文件未被修改
        # print(f"文件 {os.path.basename(plist_file_path)} 无需更新 (未找到匹配日期或状态已正确)。")
        return False, True # 文件未被修改，操作视为成功
    else: # 有条目匹配但状态已是最新
        print(f"文件 {os.path.basename(plist_file_path)} 中的日期状态已是最新，无需更新。")
        return False, True # 文件未被修改，操作视为成功


def main():
    """
    主函数，处理用户交互和文件处理流程。
    """
    print("日历更新脚本")
    print("--------------------")
    print(f"日历目录将设置为: {CALENDAR_DIR}") # 显示将使用的路径
    print("--------------------")
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
                if 1800 < target_year < 2200: # 一个合理的年份范围
                    break
                else:
                    print("请输入一个有效的年份。")
            except ValueError:
                print("输入无效，请输入数字年份。")
    else:
        print("无效选项。退出脚本。")
        return

    print(f"\n准备更新 {target_year} 年的日历文件...")

    # 1. 获取该年份的节假日数据
    year_schedule_map = fetch_holiday_data(target_year)
    if not year_schedule_map:
        print(f"未能获取 {target_year} 年的节假日数据。无法继续。")
        return

    # 2. 检查日历目录是否存在
    if not os.path.isdir(CALENDAR_DIR):
        print(f"错误：日历目录 '{CALENDAR_DIR}' 不存在。")
        print("请确认该路径是正确的，并且您有权限访问它。")
        return
    
    print(f"\n将在目录 '{CALENDAR_DIR}' 中查找 {target_year} 年的日历文件...")

    # 3. 遍历目录中的文件并处理
    total_files_processed = 0 # 处理的总文件数
    files_actually_updated = 0 # 实际被修改的文件数
    files_failed_to_update = 0 # 更新失败的文件数
    
    # 正则表达式匹配YYYY.M.0 (zh_CN) 或 YYYY.MM.0 (zh_CN) 格式的文件名
    # 例如: 2025.1.0 (zh_CN) 或 2025.10.0 (zh_CN)
    filename_pattern = re.compile(r"(\d{4})\.(\d{1,2})\.0 \(zh_CN\)")

    for filename in os.listdir(CALENDAR_DIR):
        match = filename_pattern.fullmatch(filename)
        if match:
            file_year_str = match.group(1)
            # file_month_str = match.group(2) # 月份信息，当前未使用，但可以提取

            try:
                file_year = int(file_year_str)
                if file_year == target_year:
                    total_files_processed +=1
                    plist_file_full_path = os.path.join(CALENDAR_DIR, filename)
                    # print(f"\n正在处理文件: {filename}") # 可以取消注释以获取更详细的单个文件处理日志
                    
                    modified_status, success_status = update_single_plist_file(plist_file_full_path, year_schedule_map)
                    
                    if modified_status and success_status:
                        files_actually_updated += 1
                    elif not success_status: # 如果操作不成功 (例如保存失败)
                        files_failed_to_update +=1

            except ValueError:
                print(f"警告：文件名 {filename} 中的年份格式不正确，跳过。")
                continue
    
    print("\n--------------------")
    print("脚本执行完毕。")
    if total_files_processed == 0:
        print(f"在目录 '{CALENDAR_DIR}' 中没有找到属于 {target_year} 年的日历文件。")
    else:
        print(f"共检查 {total_files_processed} 个 {target_year} 年的日历文件。")
        print(f"其中 {files_actually_updated} 个文件被成功更新。")
        if files_failed_to_update > 0:
            print(f"注意：有 {files_failed_to_update} 个文件在尝试更新时发生错误。请检查上面的日志。")
        remaining_files = total_files_processed - files_actually_updated - files_failed_to_update
        if remaining_files > 0:
             print(f"{remaining_files} 个文件无需更新或未包含与节假日数据匹配的日期。")

    print("--------------------")

if __name__ == "__main__":
    main()
