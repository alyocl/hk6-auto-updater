import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import json
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"
# =================

def get_latest_from_hkjc():
    """從香港馬會官方網站獲取最新開獎結果"""
    try:
        # 香港馬會官方開獎結果頁面
        url = "https://bet.hkjc.com/marksix/getJSON.aspx"
        params = {"lang": "zh", "date": datetime.now().strftime("%Y/%m/%d")}
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            # 嘗試解析 JSON
            data = response.json()
            if "drawResult" in data:
                numbers = [int(n) for n in data["drawResult"].split(",")[:6]]
                special = int(data["drawResult"].split(",")[6]) if "drawResult" in data else None
                return numbers, special
    except Exception as e:
        print(f"HKJC 官方來源失敗: {e}")
    return None, None

def get_latest_from_55128():
    """從備用網站 55128.cn 獲取最新開獎結果"""
    try:
        url = "https://kjh.55128.cn/hk6-history-30.htm"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            # 解析 HTML 獲取最新一期（簡化版，實際需要正則表達式）
            import re
            # 匹配最新一期的號碼格式
            pattern = r'(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s*\+\s*(\d{2})'
            matches = re.findall(pattern, response.text)
            if matches:
                latest = matches[0]
                numbers = [int(n) for n in latest[:6]]
                special = int(latest[6])
                return numbers, special
    except Exception as e:
        print(f"55128 來源失敗: {e}")
    return None, None

def update_google_sheet(numbers, special):
    """更新 Google Sheets"""
    try:
        # 從 GitHub Secrets 讀取憑證
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            print("❌ 找不到 GOOGLE_CREDENTIALS_JSON")
            return False
        
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SHEET_KEY).sheet1
        
        # 讀取現有數據，檢查是否已存在
        current_data = sheet.get_all_values()
        if len(current_data) > 1:
            # 檢查最新一期是否已是今天的號碼（比較正碼）
            latest_row = current_data[1]  # 第2行是最近一期
            latest_numbers = [int(n) for n in latest_row[:6]]
            if latest_numbers == numbers:
                print("數據已是最新，無需更新")
                return True
        
        # 插入新數據到第2行
        new_row = [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 號碼 {numbers}, 特別號 {special}")
        return True
    except Exception as e:
        print(f"更新 Google Sheets 失敗: {e}")
        return False

def main():
    print(f"開始執行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 嘗試從不同來源獲取數據
    numbers, special = get_latest_from_hkjc()
    if numbers:
        print(f"從 HKJC 獲取成功: {numbers} + {special}")
    else:
        print("HKJC 失敗，嘗試備用來源...")
        numbers, special = get_latest_from_55128()
        if numbers:
            print(f"從 55128 獲取成功: {numbers} + {special}")
    
    if numbers and special:
        update_google_sheet(numbers, special)
    else:
        print("❌ 所有來源都無法獲取數據")

if __name__ == "__main__":
    main()
