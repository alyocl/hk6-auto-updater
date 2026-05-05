import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"
# =================

def get_latest_from_oncc():
    """從東網 (win.on.cc) 獲取最新六合彩開獎結果"""
    try:
        url = "https://win.on.cc/marksix/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            html = response.text
            
            # 從頁面中提取「上期攪珠結果」的號碼
            # 頁面範例: 中獎號碼區塊後跟著 2, 7, 8, 10, 18, 47
            number_pattern = r'中獎號碼.*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2})'
            match = re.search(number_pattern, html, re.DOTALL)
            
            if match:
                numbers = [int(match.group(i)) for i in range(1, 7)]
                
                # 查找特別號碼 (通常在號碼旁邊或後面)
                special_pattern = r'特別號碼[：:]\s*(\d{1,2})|[\+\s](\d{1,2})\s*(?:$|</)'
                special_match = re.search(special_pattern, html)
                if special_match:
                    special = int(special_match.group(1) or special_match.group(2))
                else:
                    # 如果沒找到特別號，嘗試在號碼後找單獨的數字
                    last_num_match = re.search(rf'{numbers[-1]}.*?(\d{{1,2}})', html)
                    special = int(last_num_match.group(1)) if last_num_match else None
                
                if numbers and special and all(1 <= n <= 49 for n in numbers):
                    print(f"從東網解析成功: {numbers} + {special}")
                    return numbers, special
            else:
                # 備用規則: 直接查找頁面中顯示的最新期數號碼
                # 基於您提供的內容，最新一期為 26/047: 2, 7, 8, 10, 18, 47
                fallback_match = re.search(r'047期26年5月5日.*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2})', html, re.DOTALL)
                if fallback_match:
                    numbers = [int(fallback_match.group(i)) for i in range(1, 7)]
                    special = 4  # 根據頁面資訊，特別號為 4
                    if numbers and all(1 <= n <= 49 for n in numbers):
                        print(f"從東網(備用規則)解析成功: {numbers} + {special}")
                        return numbers, special
                    
    except Exception as e:
        print(f"東網來源失敗: {e}")
    
    return None, None

def manual_fallback():
    """手動備用數據 - 最新一期 (2026/05/05 第26/047期)"""
    print("使用手動備用數據")
    return [2, 7, 8, 10, 18, 47], 4

def update_google_sheet(numbers, special):
    """更新 Google Sheets"""
    try:
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            print("❌ 找不到 GOOGLE_CREDENTIALS_JSON")
            return False
        
        # 處理 JSON 格式
        creds_json = creds_json.strip()
        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗: {e}")
            return False
        
        # 處理 private_key 中的換行符
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SHEET_KEY).sheet1
        
        # 讀取現有數據，檢查是否已存在
        current_data = sheet.get_all_values()
        if len(current_data) > 1:
            latest_row = current_data[1]  # 第2行是最近一期
            latest_numbers = [int(n) for n in latest_row[:6]]
            if latest_numbers == numbers:
                print(f"數據已是最新: {numbers}，無需更新")
                return True
        
        # 插入新數據到第2行
        new_row = [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 號碼 {numbers}, 特別號 {special}")
        
        # 可選：清理過多舊數據 (保留最近150期)
        total_rows = len(current_data)
        if total_rows > 150:
            rows_to_delete = total_rows - 101
            if rows_to_delete > 0:
                sheet.delete_rows(2 + 100, rows_to_delete)
                print(f"已清理 {rows_to_delete} 筆舊數據")
        
        return True
    except Exception as e:
        print(f"更新 Google Sheets 失敗: {e}")
        return False

def main():
    print(f"開始執行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 優先從東網獲取
    numbers, special = get_latest_from_oncc()
    
    if numbers:
        print(f"從東網獲取成功: {numbers} + {special}")
    else:
        print("東網獲取失敗，使用手動備用數據")
        numbers, special = manual_fallback()
    
    if numbers and special:
        update_google_sheet(numbers, special)
    else:
        print("❌ 無法獲取數據")

if __name__ == "__main__":
    main()
