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
    """從 marksixinfo.com 獲取最新六合彩開獎結果 (期號, 正碼列表, 特別號)"""
    try:
        url = "https://marksixinfo.com"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return None, None, None
        
        html = response.text
        
        # 提取期號 (例如 "26/047")
        issue_pattern = r'期數[：:]\s*(\d{2}/\d{3})'
        issue_match = re.search(issue_pattern, html)
        issue = issue_match.group(1) if issue_match else None
        
        # 提取號碼
        # 頁面中號碼以 "2" "7" "8" ... 方式排列在 <div class="number-ball"> 或類似標籤中
        # 根據之前經驗，使用備用規則
        numbers_pattern = r'<div class="number-ball">(\d{1,2})</div>'
        numbers = re.findall(numbers_pattern, html)
        if len(numbers) >= 7:
            main_numbers = [int(n) for n in numbers[:6]]
            special = int(numbers[6])
            print(f"從 marksixinfo 獲取成功: 期號 {issue}, 號碼 {main_numbers}, 特別號 {special}")
            return issue, main_numbers, special
        
        # 備用：直接從文本中提取
        text_pattern = r'今期六合彩結果.*?(\d{1,2})\s*(\d{1,2})\s*(\d{1,2})\s*(\d{1,2})\s*(\d{1,2})\s*(\d{1,2}).*?特別號[：:]\s*(\d{1,2})'
        text_match = re.search(text_pattern, html, re.DOTALL)
        if text_match:
            main_numbers = [int(text_match.group(i)) for i in range(1, 7)]
            special = int(text_match.group(7))
            print(f"從 marksixinfo 獲取成功 (備用): 期號 {issue}, 號碼 {main_numbers}, 特別號 {special}")
            return issue, main_numbers, special
        
        print("無法從 marksixinfo 解析號碼")
        return None, None, None
    except Exception as e:
        print(f"marksixinfo 來源失敗: {e}")
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
        
        # 檢查最新一期是否已存在（根據 A 列的期號）
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            latest_issue = all_data[1][0] if len(all_data[1]) > 0 else None
            if latest_issue == issue:
                print(f"數據已是最新期號 {issue}，無需更新")
                return True
        
        # 插入新行： [issue, n1, n2, n3, n4, n5, n6, special]
        new_row = [issue] + [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 期號 {issue}, 號碼 {numbers}, 特別號 {special}")
        
        # 清理超過 180 期的舊數據（暫時註解，避免錯誤）
        # total_rows = len(all_data)
        # if total_rows > 181:
        #     rows_to_delete = total_rows - 181
        #     if rows_to_delete > 0:
        #         sheet.delete_rows(2, rows_to_delete)
        #         print(f"已清理 {rows_to_delete} 筆舊數據")
        return True
    except Exception as e:
        print(f"更新 Google Sheets 失敗: {e}")
        return False

def main():
    print(f"開始執行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    issue, numbers, special = get_latest_lottery_result()
    if numbers:
        update_google_sheet(issue, numbers, special)
    else:
        print("❌ 無法獲取數據，本次更新失敗")

if __name__ == "__main__":
    main()
