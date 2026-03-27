#!/bin/bash
# 读取当天美股日报并输出（iMessage优化版）

WORKSPACE="/Users/huangd/.openclaw/workspace"
REPORT_FILE="$WORKSPACE/daily_report_$(date +%Y%m%d).txt"

# 先生成新的iMessage格式报告
echo "📊 正在生成iMessage优化版日报..."
python3 "$WORKSPACE/skills/us-stock-quant/scripts/daily_report_imsg.py" 2>/dev/null

if [ -f "$REPORT_FILE" ]; then
    echo ""
    cat "$REPORT_FILE"
else
    echo "⚠️ 报告生成失败"
    exit 1
fi
