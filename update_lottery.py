import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"
DATA_URL = "https://lottery.hk/en/mark-six/results/"
# =================

def get_latest_lottery_result():
    """從 lottery.hk 獲取最新六合彩開獎結果"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(DATA_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            html = response.text
            
            # 方法1：查找 "Balls Drawn" 後的 ul 列表
            # 根據您提供的 HTML，結構是: Balls Drawn 後跟一個 <ul class="list-unstyled">
            balls_pattern = r'Balls Drawn.*?<ul[^>]*>(.*?)</ul>'
            balls_match = re.search(balls_pattern, html, re.DOTALL)
            
            if balls_match:
                ul_content = balls_match.group(1)
                # 提取所有號碼 (在 <li> 標籤中)
                numbers = re.findall(r'<li[^>]*>(\d{1,2})</li>', ul_content)
                if len(numbers) >= 7:
                    main_numbers = [int(n) for n in numbers[:6]]
                    special = int(numbers[6])
                    print(f"從 lottery.hk 獲取成功 (方法1): {main_numbers} + {special}")
                    return main_numbers, special
            
            # 方法2：直接從表格中提取最新一期的號碼
            # 查找 "26/047" 之後的號碼
            table_pattern = r'26/047.*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2})'
            table_match = re.search(table_pattern, html, re.DOTALL)
            if table_match:
                main_numbers = [int(table_match.group(i)) for i in range(1, 7)]
                special = int(table_match.group(7))
                print(f"從 lottery.hk 獲取成功 (方法2): {main_numbers} + {special}")
                return main_numbers, special
                    
    except Exception as e:
        print(f"lottery.hk 來源失敗: {e}")
    
    return None, None

def update_google_sheet(numbers, special):
    """更新 Google Sheets"""
    try:
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            print("❌ 找不到 GOOGLE_CREDENTIALS_JSON")
            return False
        
        creds_json = creds_json.strip()
        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗: {e}")
            return False
        
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SHEET_KEY).sheet1
        
        current_data = sheet.get_all_values()
        if len(current_data) > 1:
            latest_row = current_data[1]
            latest_numbers = [int(n) for n in latest_row[:6]]
            if latest_numbers == numbers:
                print(f"數據已是最新: {numbers}，無需更新")
                return True
        
        new_row = [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 號碼 {numbers}, 特別號 {special}")
        
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
    
    numbers, special = get_latest_lottery_result()
    
    if numbers:
        print(f"從 lottery.hk 獲取成功: {numbers} + {special}")
        update_google_sheet(numbers, special)
    else:
        print("❌ 無法獲取數據，本次更新失敗")

if __name__ == "__main__":
    main()
