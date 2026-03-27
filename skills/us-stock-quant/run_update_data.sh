#!/bin/bash
# 美股数据更新脚本
# 由 LaunchAgent 定时调用

set -e

WORKSPACE="/Users/huangd/.openclaw/workspace"
SCRIPT_DIR="$WORKSPACE/skills/us-stock-quant/scripts"

echo "🚀 开始更新美股数据 - $(date)"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 更新数据
python3 "$SCRIPT_DIR/update_stock_data.py" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 数据更新完成"
    logger -t "stock-update" "美股数据更新完成"
else
    echo "❌ 数据更新失败"
    logger -t "stock-update" "ERROR: 数据更新失败"
    exit 1
fi
