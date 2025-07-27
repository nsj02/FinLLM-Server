import pymysql
import pandas as pd

# RDS MySQL 연결
conn = pymysql.connect(
    host='finance-db.c36egosuec87.ap-northeast-2.rds.amazonaws.com',
    user='alstpdusMin',
    password='Alstpdus!!',
    database='stock_data',
    charset='utf8mb4'
)

# 금양 관련 종목 검색
print("=== 금양 관련 종목 검색 ===")
query1 = "SELECT stock_id, symbol, krx_code, name, market FROM stocks WHERE name LIKE '%금양%' ORDER BY name"
df1 = pd.read_sql(query1, conn)
print(df1)

print("\n=== 그린파워 관련 종목 검색 ===")
query2 = "SELECT stock_id, symbol, krx_code, name, market FROM stocks WHERE name LIKE '%그린파워%' ORDER BY name"
df2 = pd.read_sql(query2, conn)
print(df2)

print("\n=== 018620 종목코드 검색 ===")
query3 = "SELECT stock_id, symbol, krx_code, name, market FROM stocks WHERE krx_code = '018620' OR symbol LIKE '%018620%'"
df3 = pd.read_sql(query3, conn)
print(df3)

print("\n=== 전체 종목 수 ===")
query4 = "SELECT COUNT(*) as total_stocks FROM stocks WHERE is_active = 1"
df4 = pd.read_sql(query4, conn)
print(f"활성 종목 수: {df4.iloc[0]['total_stocks']}")

print("\n=== 샘플 종목 10개 ===")
query5 = "SELECT stock_id, symbol, krx_code, name, market FROM stocks WHERE is_active = 1 LIMIT 10"
df5 = pd.read_sql(query5, conn)
print(df5)

conn.close()