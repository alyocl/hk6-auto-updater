import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import os
from datetime import datetime

# ===== 設定區 =====
SHEET_KEY = "1N0DoSvoTjfQ_aFWkG3pOn_28MaquDSwnfiyTJqVA2Fw"  # 主表 ID（已包含 issue 列）
DATA_URL = "https://lottery.hk/en/mark-six/results/"
# =================

def get_latest_lottery_result():
    """從 lottery.hk 獲取最新六合彩開獎結果 (期號, 正碼列表, 特別號)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(DATA_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            html = response.text
            
            # 提取期號 (例如 "26/048")
            # 網頁中通常有類似 "26/048" 的文字
            issue_pattern = r'(\d{2}/\d{3})'
            issue_match = re.search(issue_pattern, html)
            issue = issue_match.group(1) if issue_match else None
            if not issue:
                print("未找到期號")
            
            # 方法1：查找 "Balls Drawn" 後的 ul 列表
            balls_pattern = r'Balls Drawn.*?<ul[^>]*>(.*?)</ul>'
            balls_match = re.search(balls_pattern, html, re.DOTALL)
            
            if balls_match:
                ul_content = balls_match.group(1)
                numbers = re.findall(r'<li[^>]*>(\d{1,2})</li>', ul_content)
                if len(numbers) >= 7:
                    main_numbers = [int(n) for n in numbers[:6]]
                    special = int(numbers[6])
                    print(f"從 lottery.hk 獲取成功: 期號 {issue}, 號碼 {main_numbers}, 特別號 {special}")
                    return issue, main_numbers, special
            
            # 備用方法：從表格中提取
            table_pattern = r'26/\d{3}.*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2})'
            table_match = re.search(table_pattern, html, re.DOTALL)
            if table_match:
                main_numbers = [int(table_match.group(i)) for i in range(1, 7)]
                special = int(table_match.group(7))
                print(f"從 lottery.hk 獲取成功 (備用): 期號 {issue}, 號碼 {main_numbers}, 特別號 {special}")
                return issue, main_numbers, special
                    
    except Exception as e:
        print(f"lottery.hk 來源失敗: {e}")
    
    return None, None, None

def update_google_sheet(issue, numbers, special):
    """更新主表：插入新一期數據（包含期號）"""
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
        
        # 檢查最新一期期號是否相同
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            # 假設 A 列是 issue
            latest_issue = all_data[1][0] if len(all_data[1]) > 0 else None
            if latest_issue == issue:
                print(f"數據已是最新期號 {issue}，無需更新")
                return True
        
        # 插入新行： [issue, n1, n2, n3, n4, n5, n6, special]
        new_row = [issue] + [str(n) for n in numbers] + [str(special)]
        sheet.insert_row(new_row, 2)
        print(f"✅ 已插入新數據: 期號 {issue}, 號碼 {numbers}, 特別號 {special}")
        
        # 清理超過 180 期的舊數據（保留標題 + 最近 180 期）
        total_rows = len(all_data)
        if total_rows > 181:  # 包含標題行，所以 181 = 1 標題 + 180 數據
            rows_to_delete = total_rows - 181
            if rows_to_delete > 0:
                sheet.delete_rows(2, rows_to_delete)  # 從第 2 行開始刪除 rows_to_delete 行
                print(f"已清理 {rows_to_delete} 筆舊數據")
        
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
