#!/usr/bin/env python3
"""
美股数据定时更新任务
每天早上更新缓存数据
"""

import sys
import os
sys.path.insert(0, '/Users/huangd/.openclaw/workspace')

from stock_cache import CachedDataLoader
from datetime import datetime

def update_stock_data():
    """更新股票数据缓存"""
    print("=" * 60)
    print(f"🕐 美股数据更新任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 核心股票池
    CORE_STOCKS = [
        # 量子计算
        'QUBT', 'IONQ', 'QBTS', 'RGTI',
        # AI半导体
        'NVDA', 'AMD', 'AVGO', 'ARM', 'MRVL',
        # 机器人
        'ISRG', 'TER', 'ROK',
        # 数据中心
        'SMCI', 'DELL', 'ANET',
        # 生物科技
        'MRNA', 'BIIB', 'GILD',
        # 太空
        'RKLB', 'ASTS',
        # 核能
        'OKLO', 'SMR', 'CCJ',
        # 基准
        'SPY', 'QQQ',
        # 科技巨头
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META'
    ]
    
    # 创建带缓存的加载器 (强制刷新缓存)
    loader = CachedDataLoader(cache_max_age_days=0)  # 0表示每次都检查
    
    print(f"\n📊 更新 {len(CORE_STOCKS)} 只股票数据...\n")
    
    success_count = 0
    failed_stocks = []
    
    for i, symbol in enumerate(CORE_STOCKS):
        print(f"[{i+1}/{len(CORE_STOCKS)}] ", end="")
        df = loader.download_with_cache(symbol, period='1y', force_refresh=True)
        if df is not None:
            success_count += 1
        else:
            failed_stocks.append(symbol)
        
        # 每5个股票暂停，避免限流
        if (i + 1) % 5 == 0 and i < len(CORE_STOCKS) - 1:
            import time
            print("  ⏸️ 暂停3秒避免限流...")
            time.sleep(3)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("📈 更新结果")
    print("=" * 60)
    print(f"✅ 成功: {success_count}/{len(CORE_STOCKS)}")
    if failed_stocks:
        print(f"❌ 失败: {failed_stocks}")
    
    # 显示缓存统计
    info = loader.cache.get_cache_info()
    print(f"\n💾 缓存统计:")
    print(f"  总股票数: {info['stock_count']}")
    print(f"  总记录数: {info['record_count']:,}")
    print(f"  数据库大小: {info['db_size_mb']:.2f} MB")
    
    print("\n✅ 更新完成!")
    return success_count

if __name__ == "__main__":
    try:
        update_stock_data()
    except Exception as e:
        print(f"\n❌ 任务失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
