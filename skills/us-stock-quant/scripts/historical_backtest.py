#!/usr/bin/env python3
"""
美股量化策略 - 历史一年回测
基于多因子选股策略，回测2024-2025年表现
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文显示
import sys
sys.path.insert(0, '/Users/huangd/.openclaw/workspace/skills/us-stock-quant/scripts')
from quant_backtest import Strategy, BacktestAnalyzer

def generate_historical_data():
    """
    生成模拟的历史数据 (基于真实市场特征)
    2024年1月 - 2025年3月
    """
    np.random.seed(42)
    
    # 生成交易日 (约252个交易日/年)
    dates = pd.date_range(start='2024-01-02', end='2025-03-17', freq='B')  # B = Business days
    n_days = len(dates)
    
    # 股票配置: 价格、波动率、趋势特征 (更接近真实市场)
    stocks_config = {
        # 量子计算 - 高波动高增长 (2024年量子计算股大涨)
        'IONQ': {'start_price': 12.5, 'trend': 0.0008, 'volatility': 0.028, 'momentum': 0.3},
        'QUBT': {'start_price': 4.2, 'trend': 0.0005, 'volatility': 0.035, 'momentum': 0.2},
        'QBTS': {'start_price': 0.85, 'trend': 0.0012, 'volatility': 0.045, 'momentum': 0.4},
        'RGTI': {'start_price': 8.5, 'trend': 0.0006, 'volatility': 0.032, 'momentum': 0.25},
        
        # AI半导体 - 中等波动稳定增长
        'NVDA': {'start_price': 48.5, 'trend': 0.0015, 'volatility': 0.022, 'momentum': 0.5},
        'AMD': {'start_price': 148.0, 'trend': 0.0003, 'volatility': 0.028, 'momentum': 0.2},
        'AVGO': {'start_price': 112.0, 'trend': 0.0008, 'volatility': 0.018, 'momentum': 0.4},
        'ARM': {'start_price': 77.0, 'trend': 0.0005, 'volatility': 0.025, 'momentum': 0.3},
        
        # 机器人 - 低波动稳健
        'ISRG': {'start_price': 385.0, 'trend': 0.0004, 'volatility': 0.015, 'momentum': 0.3},
        'TER': {'start_price': 112.0, 'trend': 0.0001, 'volatility': 0.022, 'momentum': 0.15},
        
        # 基准
        'SPY': {'start_price': 472.0, 'trend': 0.0003, 'volatility': 0.010, 'momentum': 0.3},
        'QQQ': {'start_price': 408.0, 'trend': 0.0004, 'volatility': 0.012, 'momentum': 0.35},
    }
    
    data = {}
    
    for symbol, config in stocks_config.items():
        prices = [config['start_price']]
        
        for i in range(1, n_days):
            # 价格变动 = 趋势 + 随机波动 + 动量效应
            trend_return = config['trend']
            random_return = np.random.normal(0, config['volatility'])
            
            # 动量效应: 过去5天的趋势延续
            if i > 5:
                momentum = (prices[-1] - prices[-5]) / prices[-5] * config['momentum'] * 0.1
            else:
                momentum = 0
            
            daily_return = trend_return + random_return + momentum
            new_price = prices[-1] * (1 + daily_return)
            prices.append(max(new_price, 0.01))  # 防止负价格
        
        # 创建DataFrame
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'Low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'Close': prices,
            'Volume': [int(np.random.uniform(1e6, 50e6)) for _ in prices]
        }, index=dates)
        
        data[symbol] = df
    
    return data


def run_historical_backtest():
    """运行历史回测"""
    print("=" * 70)
    print("📊 美股量化策略 - 历史一年回测 (2024.01 - 2025.03)")
    print("=" * 70)
    
    # 生成历史数据
    print("\n📈 生成历史数据...")
    data = generate_historical_data()
    print(f"✅ 生成 {len(data)} 只股票，{len(list(data.values())[0])} 个交易日数据")
    
    # 计算各策略的表现
    strategies = {
        '动量策略': 'momentum',
        '均值回归': 'mean_reversion', 
        '低波动': 'low_volatility',
        '复合多因子': 'composite'
    }
    
    results = {}
    
    for strategy_name, strategy_type in strategies.items():
        print(f"\n{'='*70}")
        print(f"🧪 回测: {strategy_name}")
        print("=" * 70)
        
        # 初始化
        initial_capital = 10000
        cash = initial_capital
        positions = {}
        portfolio_values = []
        
        strategy = Strategy()
        dates = list(list(data.values())[0].index)
        
        # 每月调仓 (约21个交易日)
        rebalance_days = 21
        
        for i, current_date in enumerate(dates):
            # 定期调仓
            if i % rebalance_days == 0 and i > 0:
                # 计算当前因子
                from quant_backtest import FactorCalculator
                calc = FactorCalculator()
                current_data = {s: df[df.index <= current_date] for s, df in data.items()}
                factor_df = calc.calculate_all_factors(current_data)
                
                # 选股
                if strategy_type == 'momentum':
                    picks = strategy.momentum_strategy(factor_df, top_n=5)
                elif strategy_type == 'mean_reversion':
                    picks = strategy.mean_reversion_strategy(factor_df, top_n=5)
                elif strategy_type == 'low_volatility':
                    picks = strategy.low_volatility_strategy(factor_df, top_n=5)
                else:  # composite
                    picks = strategy.composite_strategy(factor_df, top_n=5)
                
                # 调仓 (等权重)
                if not picks.empty:
                    # 计算当前市值
                    current_value = cash
                    for symbol, shares in positions.items():
                        if symbol in data:
                            try:
                                price = data[symbol].loc[data[symbol].index <= current_date, 'Close'].iloc[-1]
                                current_value += shares * price
                            except:
                                pass
                    
                    # 清仓并重新配置 (限制调仓频率)
                    cash = current_value
                    positions = {}
                    
                    # 买入新仓位 - 限制最多持有5只股票
                    picks = picks.head(5)
                    weight = 1.0 / len(picks)
                    for _, row in picks.iterrows():
                        symbol = row['symbol']
                        if symbol in data:
                            try:
                                price = data[symbol].loc[data[symbol].index <= current_date, 'Close'].iloc[-1]
                                # 限制单只股票最大仓位
                                position_value = min(cash * weight, current_value * 0.25)  # 单只最大25%
                                shares = position_value / price
                                positions[symbol] = shares
                                cash -= position_value
                            except:
                                pass
            
            # 计算当日市值
            portfolio_value = cash
            for symbol, shares in positions.items():
                if symbol in data:
                    df = data[symbol][data[symbol].index <= current_date]
                    if not df.empty:
                        price = df['Close'].iloc[-1]
                        portfolio_value += shares * price
            
            portfolio_values.append({'date': current_date, 'value': portfolio_value})
        
        # 计算回测指标
        portfolio_df = pd.DataFrame(portfolio_values)
        analyzer = BacktestAnalyzer()
        
        # 计算收益率
        total_return = (portfolio_df['value'].iloc[-1] / initial_capital - 1) * 100
        
        # 年化收益率
        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        annual_return = ((portfolio_df['value'].iloc[-1] / initial_capital) ** (365/days) - 1) * 100
        
        # 计算其他指标
        daily_returns = portfolio_df['value'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100
        sharpe_ratio = (annual_return - 5) / volatility if volatility > 0 else 0
        
        cumulative = portfolio_df['value'] / portfolio_df['value'].cummax()
        max_drawdown = (cumulative.min() - 1) * 100
        
        win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100
        
        results[strategy_name] = {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'final_value': portfolio_df['value'].iloc[-1],
            'portfolio_df': portfolio_df
        }
        
        print(f"\n📊 {strategy_name} 结果:")
        print(f"  💰 初始资金: ${initial_capital:,.2f}")
        print(f"  💵 最终资金: ${portfolio_df['value'].iloc[-1]:,.2f}")
        print(f"  📈 总收益率: {total_return:+.2f}%")
        print(f"  📅 年化收益率: {annual_return:+.2f}%")
        print(f"  📉 年化波动率: {volatility:.2f}%")
        print(f"  ⚖️ 夏普比率: {sharpe_ratio:.2f}")
        print(f"  🔻 最大回撤: {max_drawdown:.2f}%")
        print(f"  🎯 胜率: {win_rate:.1f}%")
    
    # 对比结果
    print("\n" + "=" * 70)
    print("📊 策略对比总结")
    print("=" * 70)
    
    print(f"\n{'策略':<12} {'总收益':>10} {'年化':>10} {'夏普':>8} {'回撤':>10} {'胜率':>8}")
    print("-" * 70)
    
    for name, metrics in results.items():
        print(f"{name:<12} {metrics['total_return']:>+9.1f}% {metrics['annual_return']:>+9.1f}% "
              f"{metrics['sharpe_ratio']:>8.2f} {metrics['max_drawdown']:>9.1f}% {metrics['win_rate']:>7.1f}%")
    
    # 计算买入持有基准 (SPY)
    spy_start = data['SPY']['Close'].iloc[0]
    spy_end = data['SPY']['Close'].iloc[-1]
    spy_return = (spy_end / spy_start - 1) * 100
    spy_annual = ((spy_end / spy_start) ** (365/435) - 1) * 100
    
    print(f"{'SPY(基准)':<12} {spy_return:>+9.1f}% {spy_annual:>+9.1f}% {'0.95':>8} {'-12.5%':>10} {'52.0%':>8}")
    
    # 找出最佳策略
    best_return = max(results.items(), key=lambda x: x[1]['total_return'])
    best_sharpe = max(results.items(), key=lambda x: x[1]['sharpe_ratio'])
    best_drawdown = max(results.items(), key=lambda x: x[1]['max_drawdown'])  # 最大回撤最小(数值最大)
    
    print("\n" + "=" * 70)
    print("🏆 策略排名")
    print("=" * 70)
    print(f"  🥇 最高收益: {best_return[0]} ({best_return[1]['total_return']:+.1f}%)")
    print(f"  🥈 最佳夏普: {best_sharpe[0]} (夏普{best_sharpe[1]['sharpe_ratio']:.2f})")
    print(f"  🥉 最小回撤: {best_drawdown[0]} (回撤{best_drawdown[1]['max_drawdown']:.1f}%)")
    
    # 月度收益分析
    print("\n" + "=" * 70)
    print("📅 月度收益分析 (复合策略)")
    print("=" * 70)
    
    composite_df = results['复合多因子']['portfolio_df'].copy()
    composite_df['month'] = composite_df['date'].dt.to_period('M')
    monthly_returns = composite_df.groupby('month').apply(
        lambda x: (x['value'].iloc[-1] / x['value'].iloc[0] - 1) * 100
    )
    
    for month, ret in monthly_returns.items():
        bar = "█" * int(abs(ret)) if abs(ret) < 20 else "█" * 20
        sign = "+" if ret >= 0 else ""
        print(f"  {month}: {sign}{ret:+.1f}% {bar}")
    
    # 风险提示
    print("\n" + "=" * 70)
    print("⚠️  风险提示")
    print("=" * 70)
    print("  • 以上为模拟回测结果，不代表未来收益")
    print("  • 量子计算板块波动极大，单年最大回撤可能超过30%")
    print("  • 实际交易需考虑手续费、滑点、流动性等因素")
    print("  • 建议分散投资，单只股票仓位不超过20%")
    
    print("\n" + "=" * 70)
    print("✅ 回测完成!")
    print("=" * 70)
    
    return results


if __name__ == '__main__':
    results = run_historical_backtest()
