import requests
import re

def get_latest_lottery_result():
    """从 lottery.hk 获取最新六合彩开奖结果 (期号, 正码列表, 特别号)"""
    url = "https://lottery.hk/liuhecai/jieguo/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # 1. 获取网页内容
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"HTTP请求失败，状态码: {response.status_code}")
            return None, None, None

        html_content = response.text

        # 2. 解析第一行数据（最新一期）
        # 用正则表达式从HTML的行首（<tr>标签内）提取数据。
        # '(.+?)' 是一个捕获组，它会捕获从 "26/" 到下一个 "|" 之间的期号，以及随后的所有数字。
        match = re.search(r'<tr>\s*<td>(.+?)</td>\s*<td>.+?</td>\s*<td>(.+?)</td>', html_content, re.DOTALL)

        if not match:
            print("无法从页面解析出最新一期数据")
            return None, None, None

        # 3. 提取并清洗数据
        issue = match.group(1).strip()  # 提取期号，如 "26/049"
        number_string = match.group(2).strip()  # 提取原始号码字符串，如 "- 9 - 17 - 26 - 41 - 42 - 47 - 8"

        # 4. 解析号码
        # 用正则表达式找出所有数字，得到一个包含7个数字字符串的列表
        all_numbers = re.findall(r'\b(\d{1,2})\b', number_string)
        # 验证是否成功提取到7个号码
        if len(all_numbers) != 7:
            print(f"号码解析失败，期望7个，实际获得{len(all_numbers)}个: {all_numbers}")
            return None, None, None

        # 将字符串数字转换为整数列表
        main_numbers = [int(num) for num in all_numbers[:6]]
        special = int(all_numbers[6])

        print(f"从 lottery.hk 成功获取: 期号 {issue}, 号码 {main_numbers}, 特别号 {special}")
        return issue, main_numbers, special

    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return None, None, None
    except Exception as e:
        print(f"解析过程中发生未知错误: {e}")
        return None, None, None
