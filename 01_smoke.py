import os

import requests
from dotenv import load_dotenv

# 读取 .env 文件里的配置
load_dotenv('bom-cleaner.env')
webhook = os.getenv("WEBHOOK")

if not webhook:
    print("❌ 读取失败：找不到 WEBHOOK，请检查 .env 文件是否在同一个文件夹里！")
else:
    print(f"✅ WEBHOOK 读取成功：{webhook[:6]}...")
    
    # 飞书安全设置要求消息里必须包含“自定义关键词”
    # 之前在飞书里设置的关键词是：BOM 清洗周报
    msg_body = {
        "msg_type": "text",
        "content": {
            "text": "BOM 清洗周报：冒烟测试成功！🎉"
        }
    }
    
    try:
        # 发送请求到飞书
        resp = requests.post(
            webhook, 
            json=msg_body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10
        )
        result = resp.json()
        
        if result.get("code") == 0:
            print("✅ 消息发送成功！请去飞书群里检查是否收到了消息。")
        else:
            print(f"❌ 消息发送失败，飞书返回错误：{result}")
            
    except Exception as e:
        print(f"❌ 请求发送失败：{e}")
