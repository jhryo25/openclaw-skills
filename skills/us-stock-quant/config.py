# Alpha Vantage API 配置
# 免费申请: https://www.alphavantage.co/support/#api-key

# 把你的 API Key 写在这里（替换 YOUR_API_KEY_HERE）
ALPHAVANTAGE_API_KEY = "YOUR_API_KEY_HERE"

# 或者从环境变量读取（推荐）
import os
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "YOUR_API_KEY_HERE")
