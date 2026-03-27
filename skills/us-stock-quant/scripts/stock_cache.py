# SQLite 本地缓存模块
# 缓存股票数据，避免重复下载

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

class StockCache:
    """股票数据本地缓存"""
    
    def __init__(self, db_path="./stock_cache.db"):
        """
        初始化缓存数据库
        
        Parameters:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建股票数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 创建元数据表 (记录最后更新时间)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_meta (
                symbol TEXT PRIMARY KEY,
                last_update DATE,
                data_source TEXT,
                record_count INTEGER
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON stock_data(symbol, date)
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ 缓存数据库初始化: {self.db_path}")
    
    def save_data(self, symbol, df, data_source="yfinance"):
        """
        保存股票数据到缓存
        
        Parameters:
            symbol: 股票代码
            df: DataFrame (需包含 Open, High, Low, Close, Volume 列)
            data_source: 数据来源
        """
        if df is None or df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        
        # 准备数据
        df_to_save = df.copy()
        df_to_save['symbol'] = symbol
        df_to_save['date'] = df_to_save.index.strftime('%Y-%m-%d')
        
        # 重命名列以匹配数据库
        column_map = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        df_to_save = df_to_save.rename(columns=column_map)
        
        # 选择需要的列
        cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        df_to_save = df_to_save[[c for c in cols if c in df_to_save.columns]]
        
        # 插入数据 (UPSERT: 存在则更新)
        for _, row in df_to_save.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO stock_data 
                (symbol, date, open, high, low, close, volume, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                row['symbol'], row['date'], row.get('open'), row.get('high'),
                row.get('low'), row.get('close'), row.get('volume')
            ))
        
        # 更新元数据
        conn.execute("""
            INSERT OR REPLACE INTO stock_meta (symbol, last_update, data_source, record_count)
            VALUES (?, DATE('now'), ?, ?)
        """, (symbol, data_source, len(df_to_save)))
        
        conn.commit()
        conn.close()
        print(f"  💾 已缓存 {symbol}: {len(df_to_save)} 条数据")
    
    def load_data(self, symbol, days=365):
        """
        从缓存加载股票数据
        
        Parameters:
            symbol: 股票代码
            days: 加载最近N天的数据
        
        Returns:
            DataFrame or None
        """
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT date, open, high, low, close, volume
            FROM stock_data
            WHERE symbol = ? AND date >= date('now', '-{} days')
            ORDER BY date
        """.format(days)
        
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        
        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        print(f"  📂 从缓存加载 {symbol}: {len(df)} 条数据")
        return df
    
    def is_fresh(self, symbol, max_age_days=1):
        """
        检查缓存是否新鲜
        
        Parameters:
            symbol: 股票代码
            max_age_days: 最大缓存天数
        
        Returns:
            bool: True表示缓存有效
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_update FROM stock_meta
            WHERE symbol = ? AND last_update >= date('now', '-{} days')
        """.format(max_age_days), (symbol,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def get_cache_info(self):
        """获取缓存统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票数量
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data")
        stock_count = cursor.fetchone()[0]
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM stock_data")
        record_count = cursor.fetchone()[0]
        
        # 缓存大小
        db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
        
        # 最近更新的股票
        cursor.execute("""
            SELECT symbol, last_update, data_source
            FROM stock_meta
            ORDER BY last_update DESC
            LIMIT 10
        """)
        recent = cursor.fetchall()
        
        conn.close()
        
        return {
            'stock_count': stock_count,
            'record_count': record_count,
            'db_size_mb': round(db_size, 2),
            'recent_updates': recent
        }
    
    def clear_cache(self, symbol=None):
        """
        清除缓存
        
        Parameters:
            symbol: 指定股票，None则清除全部
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("DELETE FROM stock_data WHERE symbol = ?", (symbol,))
            cursor.execute("DELETE FROM stock_meta WHERE symbol = ?", (symbol,))
            print(f"🗑️ 已清除 {symbol} 的缓存")
        else:
            cursor.execute("DELETE FROM stock_data")
            cursor.execute("DELETE FROM stock_meta")
            print("🗑️ 已清除全部缓存")
        
        conn.commit()
        conn.close()
    
    def list_cached_stocks(self):
        """列出所有已缓存的股票"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.symbol, m.last_update, m.record_count, m.data_source
            FROM stock_meta m
            ORDER BY m.last_update DESC
        """)
        
        stocks = cursor.fetchall()
        conn.close()
        
        return stocks


# 带缓存的数据加载器
class CachedDataLoader:
    """带本地缓存的数据加载器"""
    
    def __init__(self, cache_max_age_days=1):
        """
        Parameters:
            cache_max_age_days: 缓存有效期(天)
        """
        self.cache = StockCache()
        self.cache_max_age_days = cache_max_age_days
        
        # 尝试导入yfinance
        try:
            import yfinance as yf
            self.yf = yf
            self.has_yfinance = True
        except ImportError:
            print("⚠️ yfinance 未安装")
            self.has_yfinance = False
    
    def download_with_cache(self, symbol, period='1y', force_refresh=False):
        """
        带缓存的数据下载
        
        Parameters:
            symbol: 股票代码
            period: 数据周期
            force_refresh: 强制刷新缓存
        
        Returns:
            DataFrame or None
        """
        # 检查缓存
        if not force_refresh and self.cache.is_fresh(symbol, self.cache_max_age_days):
            df = self.cache.load_data(symbol)
            if df is not None and len(df) > 50:
                return df
        
        # 缓存无效或强制刷新，从网络下载
        if not self.has_yfinance:
            print(f"❌ 无法下载 {symbol}: yfinance 不可用")
            return None
        
        try:
            print(f"  🌐 从网络下载 {symbol}...", end=" ")
            ticker = self.yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if not df.empty and len(df) > 50:
                # 保存到缓存
                self.cache.save_data(symbol, df)
                print(f"✅ ({len(df)}条)")
                return df
            else:
                print(f"⚠️ 数据不足")
                return None
                
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def download_multiple(self, symbols, period='1y'):
        """批量下载多只股票"""
        data = {}
        print(f"\n📥 带缓存下载 {len(symbols)} 只股票...")
        
        for symbol in symbols:
            df = self.download_with_cache(symbol, period)
            if df is not None:
                data[symbol] = df
        
        print(f"✅ 成功获取 {len(data)}/{len(symbols)} 只股票")
        return data


# 使用示例
if __name__ == "__main__":
    # 初始化缓存
    cache = StockCache()
    
    # 查看缓存统计
    info = cache.get_cache_info()
    print(f"\n📊 缓存统计:")
    print(f"  股票数量: {info['stock_count']}")
    print(f"  记录数量: {info['record_count']}")
    print(f"  数据库大小: {info['db_size_mb']} MB")
    
    if info['recent_updates']:
        print(f"\n📅 最近更新:")
        for symbol, date, source in info['recent_updates']:
            print(f"  {symbol}: {date} ({source})")
    
    # 使用带缓存的加载器
    print("\n" + "="*50)
    loader = CachedDataLoader(cache_max_age_days=1)
    
    # 第一次下载会走网络
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    data = loader.download_multiple(symbols)
    
    # 第二次下载会从缓存读取
    print("\n" + "="*50)
    print("再次请求 (应从缓存读取):")
    data2 = loader.download_multiple(symbols)
