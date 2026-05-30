#!/bin/bash

TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

COLOR_RESET="\033[0m"
COLOR_RED="\033[1;31m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"

if [ ! -f "$DB_PATH" ]; then
    echo "[错误] 监控目标不存在：找不到数据库文件 $DB_PATH"
    exit 1
fi

echo "========================================================="
echo "       TermPlan 备考大盘高危科目巡检自动监控引擎          "
echo "========================================================="

# 从 SQLite 读取数据并逐行处理
sqlite3 "$DB_PATH" "SELECT subject, weight, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) FROM exams;" | while IFS="|" read -r SUBJECT WEIGHT DAYS_LEFT; do
    
    # 健壮性容错：防止读取出空行或残损数据导致的计算崩溃
    if [ -z "$SUBJECT" ] || [ -z "$WEIGHT" ] || [ -z "$DAYS_LEFT" ]; then
        continue
    fi

    # 如果考试已经过了或者就是今天，设置天数为 1 避免发生除以 0 崩溃
    if [ "$DAYS_LEFT" -le 0 ]; then
        DAYS_LEFT=1
    fi

    # 获取近 7 天该科目的打卡次数
    PUNCH_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM punch_history WHERE subject='$SUBJECT' AND punch_date >= date('now', '-7 days');")
    if [ -z "$PUNCH_COUNT" ]; then
        PUNCH_COUNT=0
    fi

    # 风险公式 = (权重 * 10) / (剩余天数 * (近7天打卡次数 + 1))
    STRESS_SCORE=$(echo "scale=2; ($WEIGHT * 10) / ($DAYS_LEFT * ($PUNCH_COUNT + 1))" | bc 2>/dev/null)

    # 如果系统没有安装 bc 导致计算失败，给一个安全默认值
    if [ -z "$STRESS_SCORE" ]; then
        STRESS_SCORE="0.00"
    fi

    # 利用 awk 来进行安全的浮点数大小关系判定
    IS_HIGH_RISK=$(echo "$STRESS_SCORE" | awk '{if ($1 > 5.0) print 1; else print 0;}')
    IS_MID_RISK=$(echo "$STRESS_SCORE" | awk '{if ($1 <= 5.0 && $1 > 2.0) print 1; else print 0;}')

    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

    # 状态评估文字
    if [ "$IS_HIGH_RISK" -eq 1 ]; then
        STATUS="[急需攻坚]"
    elif [ "$IS_MID_RISK" -eq 1 ]; then
        STATUS="[进度偏慢]"
    else
        STATUS="[状态良好]"
    fi
    echo "[$TIMESTAMP] 科目: $SUBJECT | 权重: $WEIGHT | 剩余: $DAYS_LEFT 天 | 近7天打卡: $PUNCH_COUNT 次 | 风险: $STRESS_SCORE | 评估: $STATUS"

done