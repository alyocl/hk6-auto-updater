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
    """从 lottery.hk 获取最新一期（期号以 26/ 开头）"""
    url = "https://lottery.hk/liuhecai/jieguo/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f"HTTP 错误: {resp.status_code}")
            return None, None, None

        html = resp.text

        # 匹配期号 26/XXX 并且紧跟一个 <ul class="balls"> 的 tr 行
        # 该正则从页面开头搜索，找到第一个 <td>26/数字</td> 且后面有 <ul class="balls"> 的片段
        match = re.search(
            r'<td>(\d{2}/\d{3})</td>.*?<ul class="balls">(.*?)</ul>',
            html,
            re.DOTALL
        )
        if not match:
            print("找不到任何期号与号码组合")
            return None, None, None

        issue = match.group(1).strip()
        balls_html = match.group(2)

        # 提取数字
        numbers = re.findall(r'<li[^>]*>(\d+)</li>', balls_html)
        if len(numbers) != 7:
            print(f"号码数量不对 (期号 {issue}): 预期7个，实际 {len(numbers)}")
            return None, None, None

        main_numbers = [int(n) for n in numbers[:6]]
        special = int(numbers[6])

        print(f"✅ 成功解析: 期号 {issue}, 号码 {main_numbers}, 特别号 {special}")
        return issue, main_numbers, special

    except Exception as e:
        print(f"解析失败: {e}")
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
