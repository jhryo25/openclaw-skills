# Alpha Vantage 数据源模块
# 免费API: https://www.alphavantage.co/support/#api-key

import requests
import pandas as pd
import time
from datetime import datetime

class AlphaVantageDataSource:
    """Alpha Vantage 数据源"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key=None):
        """
        初始化
        免费API Key: 去 https://www.alphavantage.co/support/#api-key 申请
        """
        self.api_key = api_key or "demo"  # 使用demo key只能获取IBM数据
        self.call_count = 0
        self.max_calls_per_day = 500  # 免费版限制
        
    def get_daily_data(self, symbol, outputsize="full"):
        """
        获取日线数据
        
        Parameters:
            symbol: 股票代码 (如 'IBM', 'AAPL')
            outputsize: 'full'(20年) 或 'compact'(100天)
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        if self.call_count >= self.max_calls_per_day:
            print(f"⚠️ 已达到每日调用限制 ({self.max_calls_per_day})")
            return None
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": outputsize,
            "datatype": "json"
        }
        
        try:
            print(f"  📥 下载 {symbol}...", end=" ")
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            data = response.json()
            
            # 检查错误
            if "Error Message" in data:
                print(f"❌ API错误: {data['Error Message']}")
                return None
            
            if "Note" in data:
                print(f"⚠️ {data['Note']}")
                return None
            
            # 解析数据
            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                print(f"❌ 无数据")
                return None
            
            df_data = []
            for date, values in data[time_series_key].items():
                df_data.append({
                    'Date': date,
                    'Open': float(values['1. open']),
                    'High': float(values['2. high']),
                    'Low': float(values['3. low']),
                    'Close': float(values['4. close']),
                    'Volume': int(values['5. volume'])
                })
            
            df = pd.DataFrame(df_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            df.set_index('Date', inplace=True)
            
            self.call_count += 1
            print(f"✅ ({len(df)}条)")
            
            # 免费版限速: 5次/分钟
            time.sleep(13)
            
            return df
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def get_intraday_data(self, symbol, interval="5min", outputsize="compact"):
        """
        获取分钟级数据
        注意: 免费版每分钟数据只返回最近100条
        """
        if self.call_count >= self.max_calls_per_day:
            print(f"⚠️ 已达到每日调用限制")
            return None
        
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "apikey": self.api_key,
            "outputsize": outputsize,
            "datatype": "json"
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            data = response.json()
            
            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                print(f"❌ 无数据: {data.get('Note', 'Unknown error')}")
                return None
            
            df_data = []
            for timestamp, values in data[time_series_key].items():
                df_data.append({
                    'Timestamp': timestamp,
                    'Open': float(values['1. open']),
                    'High': float(values['2. high']),
                    'Low': float(values['3. low']),
                    'Close': float(values['4. close']),
                    'Volume': int(values['5. volume'])
                })
            
            df = pd.DataFrame(df_data)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df = df.sort_values('Timestamp')
            df.set_index('Timestamp', inplace=True)
            
            self.call_count += 1
            print(f"✅ 下载 {symbol} ({len(df)}条)")
            
            time.sleep(13)
            return df
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def get_multiple_stocks(self, symbols):
        """
        批量获取多只股票数据
        """
        data = {}
        print(f"\n📥 使用 Alpha Vantage 下载 {len(symbols)} 只股票...")
        print(f"   API Key: {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else '***'}")
        print(f"   限速: 5次/分钟，每日限额 {self.max_calls_per_day} 次\n")
        
        for symbol in symbols:
            df = self.get_daily_data(symbol)
            if df is not None and not df.empty:
                data[symbol] = df
            
            if self.call_count >= self.max_calls_per_day:
                print(f"\n⚠️ 已达每日限制，已下载 {len(data)} 只股票")
                break
        
        return data


# 使用示例
if __name__ == "__main__":
    # 申请免费API Key: https://www.alphavantage.co/support/#api-key
    API_KEY = "YOUR_API_KEY_HERE"  # 替换为你的API Key
    
    av = AlphaVantageDataSource(api_key=API_KEY)
    
    # 获取单只股票
    df = av.get_daily_data("IBM")
    print(df.head())
    
    # 批量获取
    symbols = ["IBM", "AAPL", "MSFT", "GOOGL", "TSLA"]
    data = av.get_multiple_stocks(symbols)
    print(f"\n成功下载 {len(data)} 只股票")
