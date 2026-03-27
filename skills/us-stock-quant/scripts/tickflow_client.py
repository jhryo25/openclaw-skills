#!/usr/bin/env python3
"""
TickFlow 数据抓取客户端
用于获取市场情绪数据（涨幅榜、跌幅榜、最活跃榜）
以及股票筛选数据用于交叉验证
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re


class TickFlowClient:
    """TickFlow 数据客户端"""
    
    BASE_URL = "https://tickflow.io"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_market_movers(self):
        """
        获取市场热门榜单
        Returns: {
            'gainers': [{'symbol': 'EEIQ', 'name': '...', 'price': 8.89, 'change': '+219.04%'}, ...],
            'losers': [...],
            'most_active': [...]
        }
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/movers", timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            movers = {
                'gainers': [],
                'losers': [],
                'most_active': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            # 找到所有包含股票数据的卡片 (grid grid-cols-1 ...)
            grid = soup.find('div', class_=re.compile('grid.*gap-4'))
            if grid:
                cards = grid.find_all('div', class_=re.compile('rounded-lg.*border.*bg-'))
                
                for card in cards:
                    # 获取卡片标题
                    title_elem = card.find('span', class_=re.compile('text-sm.*font-medium'))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # 获取该卡片下的所有股票行
                    rows = card.find_all('div', class_=re.compile('flex items-center gap-2'))
                    stocks = []
                    
                    for row in rows:
                        try:
                            # 股票代码
                            symbol_elem = row.find('a', href=re.compile('/stock/'))
                            symbol = symbol_elem.get_text(strip=True) if symbol_elem else ''
                            
                            # 公司名称
                            name_elem = row.find('span', class_=re.compile('min-w-0 flex-1 truncate'))
                            name = name_elem.get_text(strip=True) if name_elem else ''
                            
                            # 价格 - 找包含 $ 的 span
                            price = 0.0
                            for span in row.find_all('span'):
                                text = span.get_text(strip=True)
                                if text.startswith('$') and '%' not in text:
                                    price = self._parse_price(text)
                                    break
                            
                            # 涨跌幅 (找带有颜色标记的百分比)
                            change_elem = row.find('span', class_=re.compile('text-(green|red)-500'))
                            change = change_elem.get_text(strip=True) if change_elem else ''
                            
                            if symbol:
                                stocks.append({
                                    'symbol': symbol,
                                    'name': name,
                                    'price': price,
                                    'change': change
                                })
                        except Exception:
                            continue
                    
                    # 根据标题分类
                    if 'Gainers' in title:
                        movers['gainers'] = stocks[:5]  # 只取前5
                    elif 'Losers' in title:
                        movers['losers'] = stocks[:5]
                    elif 'Active' in title:
                        movers['most_active'] = stocks[:5]
            
            return movers
            
        except Exception as e:
            print(f"⚠️ TickFlow 数据获取失败: {e}")
            return {'gainers': [], 'losers': [], 'most_active': [], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    def _parse_price(self, price_text):
        """解析价格文本"""
        try:
            cleaned = price_text.replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except:
            return 0.0
    
    def validate_stocks(self, symbols):
        """
        交叉验证股票列表（用 TickFlow 数据验证）
        Returns: [{'symbol': 'IONQ', 'in_gainers': True, 'in_losers': False, 'in_active': True}, ...]
        """
        movers = self.get_market_movers()
        
        # 创建快速查找集合
        gainers_set = {s['symbol'] for s in movers['gainers']}
        losers_set = {s['symbol'] for s in movers['losers']}
        active_set = {s['symbol'] for s in movers['most_active']}
        
        validations = []
        for symbol in symbols:
            validations.append({
                'symbol': symbol,
                'in_gainers': symbol in gainers_set,
                'in_losers': symbol in losers_set,
                'in_active': symbol in active_set,
                'market_heat': 'hot' if symbol in gainers_set or symbol in active_set else 'cold' if symbol in losers_set else 'normal'
            })
        
        return validations
    
    def get_market_sentiment(self):
        """
        获取市场情绪总结
        Returns: {'sentiment': 'bullish/neutral/bearish', 'score': 75}
        """
        movers = self.get_market_movers()
        
        # 简单情绪判断
        gainers_count = len(movers['gainers'])
        losers_count = len(movers['losers'])
        
        if gainers_count == 0 and losers_count == 0:
            return {
                'sentiment': 'unknown',
                'score': 50,
                'gainers_count': 0,
                'losers_count': 0
            }
        
        # 计算平均涨跌幅
        avg_gainer_change = 0
        avg_loser_change = 0
        
        if movers['gainers']:
            total = 0
            for s in movers['gainers']:
                try:
                    val = float(s['change'].replace('%', '').replace('+', ''))
                    total += val
                except:
                    pass
            avg_gainer_change = total / len(movers['gainers'])
        
        if movers['losers']:
            total = 0
            for s in movers['losers']:
                try:
                    val = float(s['change'].replace('%', '').replace('-', ''))
                    total += abs(val)
                except:
                    pass
            avg_loser_change = total / len(movers['losers'])
        
        # 情绪判断
        if avg_gainer_change > 50 or gainers_count > losers_count * 1.5:
            sentiment = 'bullish'
            score = min(50 + avg_gainer_change / 5, 90)
        elif avg_loser_change > 30 or losers_count > gainers_count * 1.5:
            sentiment = 'bearish'
            score = max(50 - avg_loser_change / 3, 20)
        else:
            sentiment = 'neutral'
            score = 50
        
        return {
            'sentiment': sentiment,
            'score': int(score),
            'gainers_count': gainers_count,
            'losers_count': losers_count,
            'avg_gainer_change': f"+{avg_gainer_change:.1f}%",
            'avg_loser_change': f"-{avg_loser_change:.1f}%"
        }


def format_movers_section(movers):
    """格式化市场热门榜单为日报格式"""
    lines = []
    
    if not movers.get('gainers') and not movers.get('losers'):
        lines.append("  ⚠️ TickFlow 数据暂未获取到")
        return "\n".join(lines)
    
    # 涨幅榜
    lines.append("🚀 今日涨幅榜 (Top Gainers)")
    lines.append("-" * 50)
    if movers['gainers']:
        for i, stock in enumerate(movers['gainers'][:5], 1):
            name = stock.get('name', '')[:18]
            lines.append(f"  {i}. {stock['symbol']:<6} {name:<20} ${stock['price']:<8.2f} {stock['change']:>10}")
    else:
        lines.append("  (暂无数据)")
    lines.append("")
    
    # 跌幅榜
    lines.append("💥 今日跌幅榜 (Top Losers)")
    lines.append("-" * 50)
    if movers['losers']:
        for i, stock in enumerate(movers['losers'][:5], 1):
            name = stock.get('name', '')[:18]
            lines.append(f"  {i}. {stock['symbol']:<6} {name:<20} ${stock['price']:<8.2f} {stock['change']:>10}")
    else:
        lines.append("  (暂无数据)")
    lines.append("")
    
    # 最活跃榜
    lines.append("🔥 今日最活跃 (Most Active)")
    lines.append("-" * 50)
    if movers['most_active']:
        for i, stock in enumerate(movers['most_active'][:5], 1):
            name = stock.get('name', '')[:18]
            lines.append(f"  {i}. {stock['symbol']:<6} {name:<20} ${stock['price']:<8.2f} {stock['change']:>10}")
    else:
        lines.append("  (暂无数据)")
    
    return "\n".join(lines)


def format_validation_section(validations, movers):
    """格式化交叉验证结果为日报格式"""
    lines = []
    
    # 统计
    hot_count = sum(1 for v in validations if v['market_heat'] == 'hot')
    cold_count = sum(1 for v in validations if v['market_heat'] == 'cold')
    
    lines.append("🔄 TickFlow 交叉验证")
    lines.append("-" * 50)
    lines.append(f"  热门股票: {hot_count} 只 | 冷门股票: {cold_count} 只")
    lines.append("")
    
    # 详细列表
    for v in validations:
        emoji = "🔥" if v['market_heat'] == 'hot' else "❄️" if v['market_heat'] == 'cold' else "⚪"
        status = []
        if v['in_gainers']:
            status.append("涨幅榜✓")
        if v['in_active']:
            status.append("活跃榜✓")
        if v['in_losers']:
            status.append("⚠️跌幅榜")
        
        status_str = ", ".join(status) if status else "无特殊状态"
        lines.append(f"  {emoji} {v['symbol']:<6} {status_str}")
    
    # 建议
    lines.append("")
    if hot_count >= 2:
        lines.append("  ✅ 市场热度较高，复合策略选股与 TickFlow 热度一致")
    elif cold_count >= 2:
        lines.append("  ⚠️ 多只股票在跌幅榜，建议谨慎操作或观望")
    else:
        lines.append("  ℹ️ 市场情绪中性，按复合策略执行")
    
    return "\n".join(lines)


if __name__ == '__main__':
    # 测试
    client = TickFlowClient()
    
    print("=" * 60)
    print("TickFlow 数据测试")
    print("=" * 60)
    
    # 获取市场热门
    print("\n获取市场热门...")
    movers = client.get_market_movers()
    print(format_movers_section(movers))
    
    # 市场情绪
    print("\n")
    print("=" * 60)
    sentiment = client.get_market_sentiment()
    print(f"市场情绪: {sentiment['sentiment']} (评分: {sentiment['score']}/100)")
    print(f"上涨: {sentiment['gainers_count']}, 下跌: {sentiment['losers_count']}")
    if 'avg_gainer_change' in sentiment:
        print(f"平均涨幅: {sentiment['avg_gainer_change']}, 平均跌幅: {sentiment['avg_loser_change']}")
    
    # 交叉验证测试
    print("\n")
    print("=" * 60)
    test_symbols = ['IONQ', 'NVDA', 'QUBT', 'SPY', 'TSLA']
    validations = client.validate_stocks(test_symbols)
    print(format_validation_section(validations, movers))
