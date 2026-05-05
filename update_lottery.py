import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"
DATA_URL = "https://marksixinfo.com"
# =================

def get_latest_from_marksixinfo():
    """從 marksixinfo.com 獲取最新六合彩開獎結果"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(DATA_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            html = response.text
            
            # 根據 HTML 結構，查找最新一期的號碼
            # 模式：在 "今期六合彩結果" 區域後，找 <div class="px-2.5...">數字</div>
            pattern = r'今期六合彩結果.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>.*?\+.*?<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                numbers = [int(match.group(i)) for i in range(1, 7)]
                special = int(match.group(7))
                
                if numbers and special and all(1 <= n <= 49 for n in numbers):
                    print(f"從 marksixinfo 獲取成功: {numbers} + {special}")
                    return numbers, special
            else:
                print("主要規則失敗，嘗試備用規則...")
                # 備用規則：直接匹配所有數字，取前7個
                all_numbers = re.findall(r'<div[^>]*class="[^"]*px-2\.5[^"]*"[^>]*>(\d{1,2})</div>', html)
                if len(all_numbers) >= 13:
                    # 最新一期是第一個區塊的6個正碼 + 1個特別號
                    numbers = [int(n) for n in all_numbers[:6]]
                    special = int(all_numbers[6])
                    print(f"備用規則獲取成功: {numbers} + {special}")
                    return numbers, special
                    
    except Exception as e:
        print(f"marksixinfo 來源失敗: {e}")
    
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
            latest_row = current_data[1]  # 第2行是最近一期
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
    
    numbers, special = get_latest_from_marksixinfo()
    
    if numbers:
        print(f"從 marksixinfo 獲取成功: {numbers} + {special}")
    else:
        print("marksixinfo 獲取失敗，使用手動備用數據")
        numbers, special = manual_fallback()
    
    if numbers and special:
        update_google_sheet(numbers, special)
    else:
        print("❌ 無法獲取數據")

if __name__ == "__main__":
    main()
