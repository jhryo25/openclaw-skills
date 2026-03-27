#!/usr/bin/env python3
"""
多板块美股量化回测框架
支持：量子计算、AI半导体、机器人、生物科技等板块
因子：动量、价值、成长、波动率
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. 股票池配置 - 多板块
# ============================================================

STOCK_UNIVERSE = {
    # 量子计算板块
    'quantum': ['QUBT', 'IONQ', 'QBTS', 'RGTI'],
    
    # AI半导体板块
    'ai_semiconductor': ['NVDA', 'AMD', 'AVGO', 'ARM', 'MRVL'],
    
    # 机器人/自动化
    'robotics': ['ISRG', 'TER', 'ROK', 'CGNX', 'ANSS'],
    
    # 数据中心/云计算
    'datacenter': ['SMCI', 'DELL', 'HPE', 'ANET', 'VRT'],
    
    # 生物科技
    'biotech': ['MRNA', 'BIIB', 'GILD', 'AMGN', 'REGN'],
    
    # 太空/卫星
    'space': ['RKLB', 'ASTS', 'SPCE', 'PL', 'VSAT'],
    
    # 铀/核能
    'nuclear': ['OKLO', 'SMR', 'CCJ', 'LEU', 'URA'],
    
    # 金融ETF对冲
    'hedge': ['SPY', 'QQQ', 'VIXY', 'SQQQ']
}

# ============================================================
# 2. 数据获取模块
# ============================================================

class DataLoader:
    """数据加载器"""
    
    def __init__(self, cache_dir='./stock_cache'):
        self.cache_dir = cache_dir
        import os
        os.makedirs(cache_dir, exist_ok=True)
    
    def download_data(self, symbols, period='1y', interval='1d'):
        """下载多只股票数据 - 带重试和延迟"""
        import time
        print(f"📥 正在下载 {len(symbols)} 只股票数据...")
        data = {}
        failed = []
        
        for i, symbol in enumerate(symbols):
            # 每5个股票延迟1秒，避免限流
            if i > 0 and i % 5 == 0:
                time.sleep(1.5)
            
            # 重试3次
            for attempt in range(3):
                try:
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period=period, interval=interval)
                    if not df.empty and len(df) > 50:
                        data[symbol] = df
                        print(f"  ✅ {symbol}: {len(df)} 条数据")
                        break
                    else:
                        if attempt == 2:
                            failed.append(symbol)
                        time.sleep(0.5)
                except Exception as e:
                    if attempt == 2:
                        print(f"  ❌ {symbol}: 下载失败 - {e}")
                        failed.append(symbol)
                    time.sleep(0.5)
        
        if failed:
            print(f"⚠️ 下载失败: {failed}")
        print(f"✅ 成功下载 {len(data)} 只股票")
        return data
    
    def get_all_sectors(self, period='1y'):
        """获取所有板块数据"""
        all_symbols = []
        for sector, symbols in STOCK_UNIVERSE.items():
            all_symbols.extend(symbols)
        return self.download_data(list(set(all_symbols)), period)

# ============================================================
# 3. 因子计算模块
# ============================================================

class FactorCalculator:
    """因子计算器"""
    
    @staticmethod
    def momentum_factor(prices, lookback=20):
        """
        动量因子: N日收益率
        逻辑: 过去N天涨得多的股票，未来可能继续涨
        """
        if len(prices) < lookback:
            return np.nan
        return (prices.iloc[-1] / prices.iloc[-lookback] - 1) * 100
    
    @staticmethod
    def volatility_factor(prices, lookback=20):
        """
        波动率因子: N日收益率标准差
        逻辑: 波动率低的股票，风险调整后收益可能更好
        """
        if len(prices) < lookback:
            return np.nan
        returns = prices.pct_change().dropna().tail(lookback)
        return returns.std() * np.sqrt(252) * 100  # 年化波动率
    
    @staticmethod
    def rsi_factor(prices, lookback=14):
        """
        RSI因子: 相对强弱指数
        逻辑: RSI在30-70之间，避免超买超卖
        """
        if len(prices) < lookback:
            return np.nan
        deltas = prices.diff()
        gain = (deltas.where(deltas > 0, 0)).rolling(window=lookback).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(window=lookback).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    @staticmethod
    def mean_reversion_factor(prices, lookback=20):
        """
        均值回归因子: 偏离均线的程度
        逻辑: 短期大涨可能回调，短期大跌可能反弹
        """
        if len(prices) < lookback:
            return np.nan
        ma = prices.rolling(lookback).mean()
        deviation = (prices.iloc[-1] - ma.iloc[-1]) / ma.iloc[-1] * 100
        return deviation
    
    @staticmethod
    def volume_factor(df, lookback=20):
        """
        量价因子: 近期成交量/历史平均成交量
        逻辑: 放量上涨更可靠
        """
        if len(df) < lookback:
            return np.nan
        recent_volume = df['Volume'].tail(5).mean()
        avg_volume = df['Volume'].tail(lookback).mean()
        return recent_volume / avg_volume if avg_volume > 0 else 1
    
    @staticmethod
    def max_drawdown_factor(prices, lookback=60):
        """
        最大回撤因子: N日内最大回撤
        逻辑: 回撤小的股票更稳健
        """
        if len(prices) < lookback:
            return np.nan
        recent_prices = prices.tail(lookback)
        peak = recent_prices.cummax()
        drawdown = (recent_prices - peak) / peak
        return drawdown.min() * 100  # 负值，越小越好
    
    @staticmethod
    def sharpe_like_factor(prices, lookback=60):
        """
        夏普率近似因子: 收益/波动
        逻辑: 单位风险带来的收益越高越好
        """
        if len(prices) < lookback:
            return np.nan
        returns = prices.pct_change().dropna().tail(lookback)
        if returns.std() == 0:
            return 0
        return (returns.mean() * 252) / (returns.std() * np.sqrt(252)) * 100
    
    @staticmethod
    def beta_factor(df, lookback=60):
        """
        Beta因子: 相对市场波动率 (使用SPY作为市场基准)
        简化版: 自身波动率与市场波动的比值
        """
        if len(df) < lookback:
            return np.nan
        # 使用价格的波动率作为代理
        returns = df['Close'].pct_change().dropna().tail(lookback)
        return returns.std() * np.sqrt(252) * 100
    
    def calculate_all_factors(self, data):
        """计算所有股票的因子"""
        factors = []
        
        for symbol, df in data.items():
            if len(df) < 50:
                continue
                
            prices = df['Close']
            
            factor_row = {
                'symbol': symbol,
                'price': prices.iloc[-1],
                'momentum_20d': self.momentum_factor(prices, 20),
                'momentum_60d': self.momentum_factor(prices, 60),
                'volatility_20d': self.volatility_factor(prices, 20),
                'rsi_14d': self.rsi_factor(prices, 14),
                'mean_reversion_20d': self.mean_reversion_factor(prices, 20),
                'volume_ratio': self.volume_factor(df, 20),
                'max_drawdown_60d': self.max_drawdown_factor(prices, 60),
                'sharpe_like_60d': self.sharpe_like_factor(prices, 60),
                'beta_60d': self.beta_factor(df, 60),
                'avg_volume_20d': df['Volume'].tail(20).mean(),
                'sector': self._get_sector(symbol)
            }
            factors.append(factor_row)
        
        return pd.DataFrame(factors)
    
    def _get_sector(self, symbol):
        """获取股票所属板块"""
        for sector, symbols in STOCK_UNIVERSE.items():
            if symbol in symbols:
                return sector
        return 'unknown'

# ============================================================
# 4. 选股策略模块
# ============================================================

class Strategy:
    """选股策略"""
    
    @staticmethod
    def momentum_strategy(factor_df, top_n=5):
        """
        动量策略: 选择20日涨幅最高的股票
        排除波动率过高的（年化>100%）
        """
        if factor_df.empty:
            return factor_df
        
        df = factor_df.copy()
        # 过滤条件 - 处理可能的NaN值
        df = df.dropna(subset=['volatility_20d', 'momentum_20d'])
        df = df[df['volatility_20d'] < 100]  # 排除过高波动
        df = df[df['avg_volume_20d'] > 1000000]  # 排除低流动性
        
        if df.empty:
            return df
        
        # 按动量排序
        df = df.sort_values('momentum_20d', ascending=False)
        return df.head(top_n)
    
    @staticmethod
    def mean_reversion_strategy(factor_df, top_n=5):
        """
        均值回归策略: 选择超跌股票（偏离均线-10%以下）
        但RSI>30（避免超卖过度）
        """
        if factor_df.empty:
            return factor_df
        
        df = factor_df.copy()
        df = df.dropna(subset=['mean_reversion_20d', 'rsi_14d'])
        df = df[df['mean_reversion_20d'] < -10]  # 超跌
        df = df[df['rsi_14d'] > 30]  # 但不过度超卖
        df = df[df['rsi_14d'] < 50]  # 且有反弹空间
        
        if df.empty:
            return df
        
        df = df.sort_values('mean_reversion_20d', ascending=True)
        return df.head(top_n)
    
    @staticmethod
    def low_volatility_strategy(factor_df, top_n=5):
        """
        低波动策略: 选择波动率最低的股票
        用于防守配置
        """
        if factor_df.empty:
            return factor_df
        
        df = factor_df.copy()
        df = df.dropna(subset=['volatility_20d', 'momentum_60d'])
        df = df[df['momentum_60d'] > -20]  # 排除长期下跌
        df = df.sort_values('volatility_20d', ascending=True)
        return df.head(top_n)
    
    @staticmethod
    def composite_strategy(factor_df, top_n=5):
        """
        复合策略: 多因子打分
        动量(40%) + 低波动(30%) + 量价配合(30%)
        """
        if factor_df.empty:
            return factor_df
        
        df = factor_df.copy()
        df = df.dropna(subset=['momentum_20d', 'volatility_20d', 'volume_ratio'])
        
        if df.empty:
            return df
        
        # 标准化打分 (0-100)
        mom_mean, mom_std = df['momentum_20d'].mean(), df['momentum_20d'].std()
        vol_mean, vol_std = df['volatility_20d'].mean(), df['volatility_20d'].std()
        
        if mom_std > 0:
            df['momentum_score'] = (df['momentum_20d'] - mom_mean) / mom_std * 50 + 50
        else:
            df['momentum_score'] = 50
        
        vol_min, vol_max = df['volatility_20d'].min(), df['volatility_20d'].max()
        if vol_max > vol_min:
            df['volatility_score'] = 100 - (df['volatility_20d'] - vol_min) / (vol_max - vol_min) * 100
        else:
            df['volatility_score'] = 50
        
        df['volume_score'] = (df['volume_ratio'] - 1) * 50 + 50
        df['volume_score'] = df['volume_score'].clip(0, 100)
        
        # 综合得分
        df['composite_score'] = (
            df['momentum_score'] * 0.4 +
            df['volatility_score'] * 0.3 +
            df['volume_score'] * 0.3
        )
        
        df = df.sort_values('composite_score', ascending=False)
        return df.head(top_n)

class BacktestAnalyzer:
    """回测结果分析器"""
    
    @staticmethod
    def calculate_metrics(portfolio_df, trades_df, initial_capital=10000):
        """计算回测指标"""
        if portfolio_df is None or portfolio_df.empty:
            return None
        
        values = portfolio_df['value']
        
        # 基础指标
        total_return = (values.iloc[-1] / initial_capital - 1) * 100
        
        # 年化收益率
        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        if days > 0:
            annual_return = ((values.iloc[-1] / initial_capital) ** (365/days) - 1) * 100
        else:
            annual_return = 0
        
        # 日收益率
        daily_returns = values.pct_change().dropna()
        
        # 波动率 (年化)
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # 夏普比率 (假设无风险利率5%)
        if volatility > 0:
            sharpe_ratio = (annual_return - 5) / volatility
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        cumulative = values / values.cummax()
        max_drawdown = (cumulative.min() - 1) * 100
        
        # 最大回撤持续时间
        peak_idx = values.cummax().idxmax()
        trough_idx = values[cumulative == cumulative.min()].index[0] if not cumulative.min() == 1 else peak_idx
        
        # 胜率 (盈利天数 / 总天数)
        win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100
        
        # 盈亏比
        avg_gain = daily_returns[daily_returns > 0].mean() * 100 if len(daily_returns[daily_returns > 0]) > 0 else 0
        avg_loss = abs(daily_returns[daily_returns < 0].mean() * 100) if len(daily_returns[daily_returns < 0]) > 0 else 1
        profit_loss_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
        
        # 卡尔玛比率 (年化收益 / |最大回撤|)
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 调仓次数
        num_trades = len(trades_df) if trades_df is not None else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'calmar_ratio': calmar_ratio,
            'num_trades': num_trades,
            'final_value': values.iloc[-1]
        }
    
    @staticmethod
    def print_report(metrics, strategy_name=""):
        """打印回测报告"""
        if metrics is None:
            print("❌ 无回测数据")
            return
        
        print("\n" + "=" * 60)
        print(f"📊 {strategy_name} 回测报告")
        print("=" * 60)
        print(f"💰 初始资金: $10,000")
        print(f"💵 最终资金: ${metrics['final_value']:.2f}")
        print(f"📈 总收益率: {metrics['total_return']:+.2f}%")
        print(f"📅 年化收益率: {metrics['annual_return']:+.2f}%")
        print(f"📉 年化波动率: {metrics['volatility']:.2f}%")
        print(f"⚖️ 夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"🔻 最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"🎯 胜率: {metrics['win_rate']:.1f}%")
        print(f"⚡ 盈亏比: {metrics['profit_loss_ratio']:.2f}")
        print(f"🏆 卡尔玛比率: {metrics['calmar_ratio']:.2f}")
        print(f"🔄 调仓次数: {metrics['num_trades']}")
        print("=" * 60)
        
        # 评级
        score = 0
        if metrics['total_return'] > 20: score += 2
        elif metrics['total_return'] > 0: score += 1
        if metrics['sharpe_ratio'] > 1: score += 2
        elif metrics['sharpe_ratio'] > 0.5: score += 1
        if abs(metrics['max_drawdown']) < 20: score += 2
        elif abs(metrics['max_drawdown']) < 30: score += 1
        
        if score >= 5:
            print("🏆 策略评级: 优秀")
        elif score >= 3:
            print("✅ 策略评级: 良好")
        elif score >= 1:
            print("⚠️ 策略评级: 一般")
        else:
            print("❌ 策略评级: 较差")
        print("=" * 60)


# ============================================================
# 5. 回测引擎
# ============================================================

class BacktestEngine:
    """简单回测引擎"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.positions = {}
        self.cash = initial_capital
        
    def run_backtest(self, data, strategy_func, rebalance_days=20, start_date=None, end_date=None):
        """
        运行回测
        rebalance_days: 调仓频率（天数）
        """
        if not data:
            return None
            
        # 获取日期范围
        dates = list(list(data.values())[0].index)
        if start_date:
            dates = [d for d in dates if d >= start_date]
        if end_date:
            dates = [d for d in dates if d <= end_date]
        
        portfolio_values = []
        trades = []
        
        for i, current_date in enumerate(dates):
            # 定期调仓
            if i % rebalance_days == 0 and i > 0:
                print(f"\n📅 调仓日期: {current_date.strftime('%Y-%m-%d')}")
                
                # 计算当前因子
                calc = FactorCalculator()
                current_data = {s: df[df.index <= current_date] for s, df in data.items()}
                factor_df = calc.calculate_all_factors(current_data)
                
                # 选股
                picks = strategy_func(factor_df)
                print(f"📊 选股结果: {list(picks['symbol'])}")
                
                # 调仓（简化：等权重分配）
                if not picks.empty:
                    self.rebalance(picks, current_date, current_data)
                    trades.append({
                        'date': current_date,
                        'holdings': list(picks['symbol']),
                        'portfolio_value': self.get_portfolio_value(current_date, current_data)
                    })
            
            # 记录每日净值
            current_data = {s: df[df.index <= current_date] for s, df in data.items()}
            portfolio_value = self.get_portfolio_value(current_date, current_data)
            portfolio_values.append({'date': current_date, 'value': portfolio_value})
        
        return pd.DataFrame(portfolio_values), trades
    
    def rebalance(self, picks, date, data):
        """执行调仓 - 简化版本"""
        # 清仓
        self.positions = {}
        self.cash = self.get_portfolio_value(date, data)
        
        # 新仓位（等权重）
        if len(picks) > 0:
            weight = 1.0 / len(picks)
            for _, row in picks.iterrows():
                symbol = row['symbol']
                if symbol in data and not data[symbol].empty:
                    price = data[symbol]['Close'].iloc[-1]
                    shares = (self.cash * weight) / price
                    self.positions[symbol] = shares
    
    def get_portfolio_value(self, date, data):
        """计算组合市值"""
        value = self.cash
        for symbol, shares in self.positions.items():
            if symbol in data and not data[symbol].empty:
                df = data[symbol][data[symbol].index <= date]
                if not df.empty:
                    price = df['Close'].iloc[-1]
                    value += shares * price
        return value

# ============================================================
# 6. 主程序
# ============================================================

def main():
    print("=" * 60)
    print("🦞 多板块美股量化回测系统")
    print("=" * 60)
    
    # 1. 下载数据 - 先测试核心股票
    loader = DataLoader()
    
    # 选择核心股票池 (避免限流)
    core_symbols = ['QUBT', 'IONQ', 'NVDA', 'AMD', 'AVGO', 'SPY', 'QQQ', 'TSLA', 'AAPL', 'MSFT']
    print(f"🎯 核心测试股票: {core_symbols}")
    
    data = loader.download_data(core_symbols, period='1y')
    
    if len(data) < 5:
        print(f"⚠️ 只下载了 {len(data)} 只股票，数据不足，使用演示数据...")
        # 使用缓存或演示模式
        return run_demo_mode()
    
    # 2. 计算因子
    print("\n📊 计算因子中...")
    calc = FactorCalculator()
    factor_df = calc.calculate_all_factors(data)
    
    print(f"\n✅ 成功计算 {len(factor_df)} 只股票的因子")
    print("\n📊 新因子统计 (含最大回撤、夏普率近似、Beta):")
    print(factor_df[['momentum_20d', 'volatility_20d', 'rsi_14d', 'max_drawdown_60d', 'sharpe_like_60d']].describe())
    
    # 3. 运行策略
    strategy = Strategy()
    
    print("\n" + "=" * 60)
    print("📈 策略选股结果")
    print("=" * 60)
    
    # 动量策略
    print("\n🔥 动量策略 (20日涨幅最高):")
    momentum_picks = strategy.momentum_strategy(factor_df, top_n=5)
    print(momentum_picks[['symbol', 'sector', 'price', 'momentum_20d', 'volatility_20d', 'sharpe_like_60d']].to_string(index=False))
    
    # 均值回归策略
    print("\n🎯 均值回归策略 (超跌反弹):")
    mr_picks = strategy.mean_reversion_strategy(factor_df, top_n=5)
    if not mr_picks.empty:
        print(mr_picks[['symbol', 'sector', 'price', 'mean_reversion_20d', 'rsi_14d', 'max_drawdown_60d']].to_string(index=False))
    else:
        print("  当前没有符合条件的股票")
    
    # 低波动策略
    print("\n🛡️ 低波动策略 (防守配置):")
    lv_picks = strategy.low_volatility_strategy(factor_df, top_n=5)
    print(lv_picks[['symbol', 'sector', 'price', 'volatility_20d', 'momentum_60d', 'sharpe_like_60d']].to_string(index=False))
    
    # 复合策略
    print("\n⚖️ 复合多因子策略:")
    composite_picks = strategy.composite_strategy(factor_df, top_n=5)
    print(composite_picks[['symbol', 'sector', 'price', 'composite_score', 'sharpe_like_60d']].to_string(index=False))
    
    # 4. 板块分析
    print("\n" + "=" * 60)
    print("🌍 板块表现分析")
    print("=" * 60)
    sector_analysis = factor_df.groupby('sector').agg({
        'momentum_20d': 'mean',
        'momentum_60d': 'mean',
        'volatility_20d': 'mean',
        'sharpe_like_60d': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'})
    sector_analysis = sector_analysis.sort_values('momentum_20d', ascending=False)
    print(sector_analysis.to_string())
    
    # 5. 保存结果
    factor_df.to_csv('factor_analysis.csv', index=False)
    print("\n💾 详细因子数据已保存到 factor_analysis.csv")
    
    # 6. 回测演示
    print("\n" + "=" * 60)
    print("🧪 策略回测演示")
    print("=" * 60)
    run_backtest_demo(data, strategy)
    
    print("\n" + "=" * 60)
    print("✅ 分析完成！")
    print("=" * 60)
    
    return factor_df


def run_backtest_demo(data, strategy):
    """运行回测演示"""
    print("\n⚠️ 回测功能需要完整历史数据，这里展示框架...")
    print("实际使用时，建议:")
    print("  1. 下载3-5年数据")
    print("  2. 设置月度/季度调仓")
    print("  3. 对比买入持有基准")
    
    # 模拟回测指标计算
    analyzer = BacktestAnalyzer()
    
    # 模拟一个投资组合净值曲线
    dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, 252)  # 模拟日收益
    values = 10000 * np.cumprod(1 + returns)
    
    portfolio_df = pd.DataFrame({
        'date': dates,
        'value': values
    })
    
    metrics = analyzer.calculate_metrics(portfolio_df, None)
    analyzer.print_report(metrics, "示例策略")


def run_demo_mode():
    """演示模式 - 使用模拟数据展示完整报告"""
    print("\n📊 演示模式 - 生成完整选股报告")
    print("=" * 60)
    
    np.random.seed(42)
    
    # 创建模拟数据 - 多板块
    demo_data = [
        # 量子计算
        {'symbol': 'QUBT', 'price': 7.30, 'momentum_20d': 46.55, 'momentum_60d': 38.20,
         'volatility_20d': 67.89, 'rsi_14d': 72.5, 'mean_reversion_20d': 8.5,
         'volume_ratio': 1.45, 'max_drawdown_60d': -28.50, 'sharpe_like_60d': 0.85,
         'beta_60d': 68.0, 'avg_volume_20d': 15e6, 'sector': 'quantum'},
        {'symbol': 'IONQ', 'price': 45.20, 'momentum_20d': 52.30, 'momentum_60d': 89.50,
         'volatility_20d': 45.32, 'rsi_14d': 78.2, 'mean_reversion_20d': 12.3,
         'volume_ratio': 2.10, 'max_drawdown_60d': -15.20, 'sharpe_like_60d': 1.65,
         'beta_60d': 45.0, 'avg_volume_20d': 28e6, 'sector': 'quantum'},
        {'symbol': 'QBTS', 'price': 1.85, 'momentum_20d': 38.50, 'momentum_60d': 156.80,
         'volatility_20d': 82.45, 'rsi_14d': 81.5, 'mean_reversion_20d': 18.6,
         'volume_ratio': 3.20, 'max_drawdown_60d': -25.80, 'sharpe_like_60d': 1.25,
         'beta_60d': 82.0, 'avg_volume_20d': 45e6, 'sector': 'quantum'},
        
        # AI半导体
        {'symbol': 'NVDA', 'price': 135.80, 'momentum_20d': 18.25, 'momentum_60d': 42.60,
         'volatility_20d': 42.15, 'rsi_14d': 65.8, 'mean_reversion_20d': 5.2,
         'volume_ratio': 1.25, 'max_drawdown_60d': -12.50, 'sharpe_like_60d': 1.45,
         'beta_60d': 42.0, 'avg_volume_20d': 120e6, 'sector': 'ai_semiconductor'},
        {'symbol': 'AMD', 'price': 118.50, 'momentum_20d': -5.20, 'momentum_60d': 8.50,
         'volatility_20d': 48.60, 'rsi_14d': 48.5, 'mean_reversion_20d': -3.5,
         'volume_ratio': 0.95, 'max_drawdown_60d': -18.60, 'sharpe_like_60d': 0.65,
         'beta_60d': 49.0, 'avg_volume_20d': 85e6, 'sector': 'ai_semiconductor'},
        {'symbol': 'AVGO', 'price': 185.20, 'momentum_20d': 8.50, 'momentum_60d': 15.30,
         'volatility_20d': 28.50, 'rsi_14d': 58.2, 'mean_reversion_20d': 2.8,
         'volume_ratio': 1.05, 'max_drawdown_60d': -8.50, 'sharpe_like_60d': 1.85,
         'beta_60d': 29.0, 'avg_volume_20d': 25e6, 'sector': 'ai_semiconductor'},
        
        # 机器人
        {'symbol': 'ISRG', 'price': 525.80, 'momentum_20d': 12.80, 'momentum_60d': 22.50,
         'volatility_20d': 25.40, 'rsi_14d': 62.5, 'mean_reversion_20d': 4.2,
         'volume_ratio': 0.85, 'max_drawdown_60d': -10.20, 'sharpe_like_60d': 1.55,
         'beta_60d': 25.0, 'avg_volume_20d': 3e6, 'sector': 'robotics'},
        
        # 基准
        {'symbol': 'SPY', 'price': 598.50, 'momentum_20d': 5.20, 'momentum_60d': 8.60,
         'volatility_20d': 18.50, 'rsi_14d': 55.8, 'mean_reversion_20d': 1.5,
         'volume_ratio': 1.00, 'max_drawdown_60d': -5.20, 'sharpe_like_60d': 0.95,
         'beta_60d': 18.0, 'avg_volume_20d': 65e6, 'sector': 'benchmark'},
        {'symbol': 'QQQ', 'price': 520.80, 'momentum_20d': 8.60, 'momentum_60d': 15.20,
         'volatility_20d': 22.50, 'rsi_14d': 62.5, 'mean_reversion_20d': 3.2,
         'volume_ratio': 1.15, 'max_drawdown_60d': -8.50, 'sharpe_like_60d': 1.15,
         'beta_60d': 23.0, 'avg_volume_20d': 48e6, 'sector': 'benchmark'},
    ]
    
    factor_df = pd.DataFrame(demo_data)
    strategy = Strategy()
    
    # ========== 选股报告 ==========
    print("\n" + "=" * 60)
    print("📈 策略选股结果")
    print("=" * 60)
    
    # 动量策略
    print("\n🔥 动量策略 (20日涨幅最高，排除过高波动):")
    momentum_picks = strategy.momentum_strategy(factor_df, top_n=5)
    if not momentum_picks.empty:
        display_cols = ['symbol', 'sector', 'price', 'momentum_20d', 'volatility_20d', 'sharpe_like_60d']
        print(momentum_picks[display_cols].to_string(index=False))
        print(f"\n  📌 推荐买入: {', '.join(momentum_picks['symbol'].tolist())}")
    else:
        print("  当前没有符合条件的股票")
    
    # 均值回归策略
    print("\n🎯 均值回归策略 (超跌反弹，RSI>30):")
    mr_picks = strategy.mean_reversion_strategy(factor_df, top_n=5)
    if not mr_picks.empty:
        display_cols = ['symbol', 'sector', 'price', 'mean_reversion_20d', 'rsi_14d', 'max_drawdown_60d']
        print(mr_picks[display_cols].to_string(index=False))
        print(f"\n  📌 反弹机会: {', '.join(mr_picks['symbol'].tolist())}")
    else:
        print("  当前没有符合条件的股票")
    
    # 低波动策略
    print("\n🛡️ 低波动策略 (防守配置，排除长期下跌):")
    lv_picks = strategy.low_volatility_strategy(factor_df, top_n=5)
    if not lv_picks.empty:
        display_cols = ['symbol', 'sector', 'price', 'volatility_20d', 'momentum_60d', 'sharpe_like_60d']
        print(lv_picks[display_cols].to_string(index=False))
        print(f"\n  📌 防守标的: {', '.join(lv_picks['symbol'].tolist())}")
    
    # 复合策略
    print("\n⚖️ 复合多因子策略 (综合评分):")
    composite_picks = strategy.composite_strategy(factor_df, top_n=5)
    if not composite_picks.empty:
        display_cols = ['symbol', 'sector', 'price', 'composite_score', 'sharpe_like_60d', 'momentum_20d']
        print(composite_picks[display_cols].to_string(index=False))
        print(f"\n  📌 综合推荐: {', '.join(composite_picks['symbol'].tolist())}")
    
    # ========== 板块分析 ==========
    print("\n" + "=" * 60)
    print("🌍 板块表现分析")
    print("=" * 60)
    sector_analysis = factor_df.groupby('sector').agg({
        'momentum_20d': 'mean',
        'momentum_60d': 'mean',
        'volatility_20d': 'mean',
        'sharpe_like_60d': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'}).round(2)
    sector_analysis = sector_analysis.sort_values('momentum_20d', ascending=False)
    print(sector_analysis.to_string())
    
    print(f"\n  🏆 最强板块: {sector_analysis.index[0]} (20日动量 +{sector_analysis.iloc[0]['momentum_20d']:.1f}%)")
    
    # ========== 回测统计 ==========
    print("\n" + "=" * 60)
    print("📊 策略回测模拟")
    print("=" * 60)
    
    analyzer = BacktestAnalyzer()
    
    # 模拟各策略收益
    strategies = {
        '动量策略': {'return': 35.2, 'sharpe': 1.35, 'drawdown': -18.5, 'win_rate': 56.0},
        '均值回归': {'return': 18.5, 'sharpe': 0.95, 'drawdown': -12.3, 'win_rate': 48.5},
        '低波动': {'return': 12.8, 'sharpe': 1.65, 'drawdown': -8.5, 'win_rate': 52.0},
        '复合多因子': {'return': 28.6, 'sharpe': 1.45, 'drawdown': -14.2, 'win_rate': 58.3}
    }
    
    print("\n策略对比:")
    print(f"{'策略':<12} {'收益率':>10} {'夏普':>8} {'最大回撤':>10} {'胜率':>8}")
    print("-" * 60)
    for name, metrics in strategies.items():
        print(f"{name:<12} {metrics['return']:>+9.1f}% {metrics['sharpe']:>8.2f} {metrics['drawdown']:>9.1f}% {metrics['win_rate']:>7.1f}%")
    
    print(f"\n  🏆 最佳收益: 动量策略 (+35.2%)")
    print(f"  🛡️ 最佳风险收益比: 低波动策略 (夏普1.65)")
    print(f"  ⚖️ 最均衡: 复合多因子策略 (夏普1.45, 胜率58.3%)")
    
    # ========== 持仓建议 ==========
    print("\n" + "=" * 60)
    print("💰 持仓配置建议")
    print("=" * 60)
    print("基于你的持仓: QUBT: 10股 @ $12成本, 现金: $1200")
    print("-" * 60)
    print("\n📌 QUBT 分析:")
    qubt_data = factor_df[factor_df['symbol'] == 'QUBT'].iloc[0]
    print(f"  • 当前价: ${qubt_data['price']:.2f}")
    print(f"  • 20日动量: {qubt_data['momentum_20d']:+.1f}%")
    print(f"  • RSI: {qubt_data['rsi_14d']:.1f}")
    print(f"  • 夏普率: {qubt_data['sharpe_like_60d']:.2f}")
    print(f"  • 建议: {'🔴 卖出' if qubt_data['rsi_14d'] > 80 else '🟡 持有' if qubt_data['rsi_14d'] > 50 else '🟢 加仓'}")
    
    print("\n📌 $1200 现金配置建议 (复合策略):")
    if not composite_picks.empty:
        allocation = min(len(composite_picks), 4)
        weights = [40, 30, 20, 10][:allocation]
        for i, (_, row) in enumerate(composite_picks.head(allocation).iterrows()):
            amount = 1200 * weights[i] / 100
            shares = int(amount / row['price'])
            print(f"  {i+1}. {row['symbol']} ({row['sector']}) - ${amount:.0f} ({weights[i]}%) - 约{shares}股")
    
    print("\n⚠️ 风险提示: 量子计算股波动极大，建议分批建仓，单笔不超过30%仓位！")
    
    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print("📝 今日操作总结")
    print("=" * 60)
    print("✅ QUBT: 继续持有，RSI偏高但动量强劲")
    print("✅ 现金: 优先配置 IONQ (40%) + AVGO (30%)")
    print("✅ 关注: QBTS 波动过大，谨慎追高")
    print("✅ 防守: 可配置10% SPY 对冲风险")
    
    print("\n" + "=" * 60)
    print("✅ 分析完成！")
    print("=" * 60)
    print("\n💡 提示: 以上为演示数据，实际运行需配置Alpha Vantage API")
    
    return factor_df

if __name__ == '__main__':
    main()
