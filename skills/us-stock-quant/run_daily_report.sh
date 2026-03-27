#!/bin/bash
# 美股量化日报生成并发送脚本
# 由 LaunchAgent 定时调用

set -e

WORKSPACE="/Users/huangd/.openclaw/workspace"
SCRIPT_DIR="$WORKSPACE/skills/us-stock-quant/scripts"
REPORT_FILE="$WORKSPACE/daily_report_$(date +%Y%m%d).txt"
TODAY=$(date +%Y-%m-%d)

echo "🚀 开始生成美股日报 - $(date)"

# 1. 生成日报
python3 "$SCRIPT_DIR/daily_report.py" > "$REPORT_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 日报生成成功: $REPORT_FILE"
    
    # 2. 通过 openclaw 发送到飞书
    # 使用 openclaw message 命令发送到指定群聊
    REPORT_CONTENT=$(cat "$REPORT_FILE")
    
    # 发送消息到飞书（使用 openclaw CLI）
    # 注意：这里假设 openclaw 支持发送消息到指定 channel
    # 如果不支持，可以通过 webhook 方式
    
    # 方法1: 如果 openclaw 支持直接发送
    # openclaw message send --channel feishu --content "$REPORT_CONTENT"
    
    # 方法2: 使用本地 OpenClaw API（如果运行中）
    # 通过调用本地 OpenClaw 实例来发送消息
    
    # 方法3: 写入到特殊文件，由 OpenClaw 监控并发送
    # 将报告复制到待发送目录
    mkdir -p "$WORKSPACE/pending_reports"
    cp "$REPORT_FILE" "$WORKSPACE/pending_reports/report_$TODAY.txt"
    
    echo "📤 报告已准备发送，等待 OpenClaw 推送"
    logger -t "stock-report" "美股日报已生成并准备发送: $REPORT_FILE"
    
    # 可选：弹出本地通知
    osascript -e "display notification \"美股日报已生成并准备发送\" with title \"量化系统\""
    
else
    echo "❌ 日报生成失败"
    logger -t "stock-report" "ERROR: 日报生成失败"
    exit 1
fi
