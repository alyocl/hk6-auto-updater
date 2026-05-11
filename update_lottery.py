import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"
# 注意：下方 URL 已改為我們要抓取的頁面
DATA_URL = "https://lottery.hk/liuhecai/jieguo/"
# =================

def get_latest_lottery_result():
    """從 lottery.hk 的 HTML 直接解析最新一期"""
    url = "https://lottery.hk/liuhecai/jieguo/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f"HTTP 錯誤: {resp.status_code}")
            return None, None, None

        html = resp.text

        # 1. 定位第一個有效的 tbody 之後的第一個 tr（非 tshead）
        # 用正則找出 <tbody> 後緊接著的 <tr> 內容（不包含 th）
        match = re.search(
            r'<tbody>.*?<tr>(?!.*tshead).*?<td>([^<]+)</td>.*?<ul class="balls">(.*?)</ul>',
            html,
            re.DOTALL
        )
        if not match:
            print("無法定位最新一期表格行")
            return None, None, None

        issue = match.group(1).strip()          # 例如 "26/049"
        balls_html = match.group(2)              # <li class="-blue">9</li> ...

        # 2. 從 <li> 標籤中提取所有數字（共七個）
        numbers = re.findall(r'<li[^>]*>(\d+)</li>', balls_html)
        if len(numbers) != 7:
            print(f"號碼數量不對，預期 7 個，實際 {len(numbers)} 個: {numbers}")
            return None, None, None

        main_numbers = [int(n) for n in numbers[:6]]
        special = int(numbers[6])

        print(f"✅ 成功解析: 期號 {issue}, 號碼 {main_numbers}, 特別號 {special}")
        return issue, main_numbers, special

    except Exception as e:
        print(f"解析失敗: {e}")
        return None, None, None

def update_google_sheet(issue, numbers, special):
    try:
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            print("❌ 找不到 GOOGLE_CREDENTIALS_JSON")
            return False

        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_KEY).sheet1

        # 檢查最新一期是否已存在
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            latest_issue = all_data[1][0] if len(all_data[1]) > 0 else None
            if latest_issue == issue:
                print(f"數據已是最新期號 {issue}，無需更新")
                return True

        # 插入新行
        new_row = [issue] + [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 期號 {issue}, 號碼 {numbers}, 特別號 {special}")
        return True
    except Exception as e:
        print(f"更新 Google Sheets 失敗: {e}")
        return False

def main():
    print(f"開始執行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    issue, numbers, special = get_latest_lottery_result()
    if issue and numbers:
        update_google_sheet(issue, numbers, special)
    else:
        print("❌ 無法獲取數據，本次更新失敗")

if __name__ == "__main__":
    main()
