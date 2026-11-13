
import os
import re

import lark_oapi as lark
import pandas as pd
import requests
from dotenv import load_dotenv
from lark_oapi.api.bitable.v1 import (AppTableRecord,
                                      CreateAppTableRecordRequest,
                                      ListAppTableFieldRequest,
                                      ListAppTableRecordRequest)

# 1. 加载配置
load_dotenv('bom-cleaner-202611122359.env')  # 改为默认读取 .env
WEBHOOK = os.getenv("WEBHOOK")
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
APP_TOKEN = os.getenv("APP_TOKEN")
TABLE_MAIN = os.getenv("TABLE_MAIN")
TABLE_ERR = os.getenv("TABLE_ERR")

# ... 其余函数不变，只修改 read_feishu_table 和 write_feishu_table
#client = lark.Client.builder() \
    #.app_id(APP_ID) \
    #.app_secret(APP_SECRET) \
    #.build()


# 在写入前执行一次：查询表格里的真实字段

# 2. 初始化飞书客户端
client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
print("🔍 正在查询飞书表格的真实字段...")
field_resp = client.bitable.v1.app_table_field.list(
    ListAppTableFieldRequest.builder()
    .app_token(APP_TOKEN)
    .table_id(TABLE_MAIN) # 确保这是"BOM主数据"的ID
    .build()
)
if field_resp.success():
    for f in field_resp.data.items:
        print(f"字段名: {f.field_name}, 字段ID: {f.field_id}, 类型: {f.type}")
else:
    print(f"❌ 查询字段失败: {field_resp.msg}")
# 3. BOM 清洗逻辑
def clean_bom_data(df):
    print("📦 开始清洗 BOM 数据...")
    # TODO: 根据你的实际列名修改以下规则
    if 'Manufacturer_PN' in df.columns:
        # 去除空格/全角空格、转大写
        df['Manufacturer_PN'] = df['Manufacturer_PN'].apply(
            lambda x: re.sub(r'[\s\u3000]+', '', str(x)).upper() if pd.notna(x) else None
        )
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'].astype(str).str.strip(), errors='coerce').fillna(1).astype(int)
        
    print("✅ 清洗完成！")
    return df

# 4. 读取飞书多维表格
def read_feishu_table(table_id):
    print(f"📥 正在读取飞书表格 {table_id}...")
    response = client.bitable.v1.app_table_record.list(
        ListAppTableRecordRequest.builder()  # ✅ 已修正
        .app_token(APP_TOKEN)
        .table_id(table_id)
        .build()
    )
    if not response.success():
        print(f"❌ 读取失败: {response.msg}")
        return None
    # ✅ 加上这几行防御代码
    if response.data is None or response.data.items is None:
        print("ℹ️ 表格是空的，没有读到数据。")
        return pd.DataFrame()# 返回空的DataFrame，防止后面崩溃
    records = response.data.items
    data = [r.fields for r in records]  # 假设每个 record 都有 fields 属性
    return pd.DataFrame(data)



# 5. 写入飞书多维表格
def write_feishu_table(table_id, df):
    print(f"📤 正在写入飞书表格 {table_id}...")
    for _, row in df.iterrows():
        fields = {
            "文本": str(row.get("文本", "")),
            "制造商料号":str(row.get("制造商料号", "")),
            "数量": str(row.get("数量", "")),
        }
        #fields = row.to_dict() # 需确保字典key与飞书表格列名完全一致
        print(f"🔍 准备写入的数据: {fields}") # 加上这行
        request = CreateAppTableRecordRequest.builder() \
            .app_token(APP_TOKEN) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder().fields(fields).build()) \
            .build()
        response = client.bitable.v1.app_table_record.create(request)
        if not response.success():
            print(f"❌ 写入失败: {response.msg}")


# 6. 推送结果到飞书群
def send_to_feishu(message):
    if not WEBHOOK: return
    headers = {"Content-Type": "application/json"}
    data = {"msg_type": "text", "content": {"text": message}}
    requests.post(WEBHOOK, headers=headers, json=data)

# 7. 主流程
if __name__ == "__main__":
    # 读取主表
    main_df = read_feishu_table(TABLE_MAIN)
    if main_df is not None:
        # 清洗数据
        cleaned_df = clean_bom_data(main_df)
        
        write_feishu_table(TABLE_MAIN, cleaned_df)
        # 示例：将清洗后的错误数据写入错误表
        #err_df = cleaned_df[cleaned_df['数量'] <= 0]
        #write_feishu_table(TABLE_ERR, err_df)
        
        # 发送通知
        report = f"BOM 清洗周报：成功处理 {len(cleaned_df)} 条数据！🎉"
        send_to_feishu(report)
