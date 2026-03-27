#!/usr/bin/env python3
"""
Tavily 实时股价获取模块 - 简化版
使用 Tavily 命令行工具获取股价
"""

import subprocess
import json
import re
import os

def get_stock_price_tavily(symbol):
    """
    使用 Tavily 搜索获取单只股票实时价格
    
    Args:
        symbol: 股票代码，如 'QUBT'
    
    Returns:
        float: 股价，失败返回 None
    """
    try:
        # 构建搜索查询
        query = f"{symbol} stock price today"
        
        # 调用 Tavily 搜索脚本
        script_path = '/Users/huangd/.openclaw/workspace/skills/tavily-search/scripts/tavily_search.py'
        result = subprocess.run(
            ['python3', script_path, query, '--json'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"  ⚠️ Tavily 搜索失败: {result.stderr}")
            return None
        
        # 解析 JSON 输出
        # 找到 JSON 开始的行（跳过警告信息）
        lines = result.stdout.strip().split('\n')
        json_line = None
        for line in lines:
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                json_line = line
                break
        
        if not json_line:
            return None
        
        data = json.loads(json_line)
        
        # 从 AI Answer 中提取价格
        answer = data.get('answer', '')
        if answer:
            # 匹配 "SYMBOL is $X.XX" 或 "$X.XX"
            patterns = [
                rf'{symbol}[\s\w]*(?:is|at|trading at)[\s]*\$?([\d,]+\.?\d*)',
                rf'\$([\d,]+\.?\d{2})[\s\w]*{symbol}',
            ]
            for pattern in patterns:
                match = re.search(pattern, answer, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1).replace(',', '')
                        return float(price_str)
                    except:
                        pass
        
        # 从搜索结果中查找
        results = data.get('results', [])
        for result in results:
            content = result.get('content', '')
            # 查找 "symbol is $X.XX" 或 "$X.XX USD"
            pattern = rf'{symbol}[\s\w]*\$([\d,]+\.?\d{2})'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
                except:
                    pass
            
            # 反向查找 "$X.XX ... symbol"
            pattern2 = rf'\$([\d,]+\.?\d{2})[\s\w]*{symbol}'
            match2 = re.search(pattern2, content, re.IGNORECASE)
            if match2:
                try:
                    price_str = match2.group(1).replace(',', '')
                    return float(price_str)
                except:
                    pass
        
        return None
        
    except Exception as e:
        print(f"  ⚠️ 获取 {symbol} 价格失败: {e}")
        return None


def get_multiple_prices(symbols):
    """
    获取多只股票价格
    
    Args:
        symbols: 股票代码列表
    
    Returns:
        dict: {symbol: price}
    """
    prices = {}
    for symbol in symbols:
        print(f"  查询 {symbol}...", end=" ")
        price = get_stock_price_tavily(symbol)
        if price:
            prices[symbol] = price
            print(f"${price:.2f}")
        else:
            print("失败")
    return prices


if __name__ == '__main__':
    # 测试
    test_symbols = ['QUBT', 'IONQ', 'NVDA', 'AVGO']
    print(f"测试获取股票价格: {test_symbols}")
    print()
    prices = get_multiple_prices(test_symbols)
    
    print()
    print("=" * 40)
    print("汇总:")
    for symbol, price in prices.items():
        print(f"  {symbol}: ${price:.2f}")
