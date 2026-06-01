#!/bin/bash

TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

# 获取当前用户 ID
USER_ID=${TERMPLAN_USER_ID:-0}
if [ "$USER_ID" -eq 0 ]; then
    echo "[警告] 未检测到当前登录用户，可能无法正确过滤个人数据"
fi

COLOR_RESET="\033[0m"
COLOR_RED="\033[1;31m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"

if [ ! -f "$DB_PATH" ]; then
    echo "[错误] 监控目标不存在：找不到数据库文件 $DB_PATH"
    exit 1
fi

echo "       TermPlan 备考大盘高危科目巡检自动监控引擎          "

# 从 SQLite 读取当前用户的数据
sqlite3 "$DB_PATH" "SELECT subject, weight, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) FROM exams WHERE user_id = $USER_ID;" | while IFS="|" read -r SUBJECT WEIGHT DAYS_LEFT; do
    
    if [ -z "$SUBJECT" ] || [ -z "$WEIGHT" ] || [ -z "$DAYS_LEFT" ]; then
        continue
    fi

    if [ "$DAYS_LEFT" -le 0 ]; then
        DAYS_LEFT=1
    fi

    # 查询当前用户的打卡次数
    PUNCH_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM punch_history WHERE user_id = $USER_ID AND subject='$SUBJECT' AND punch_date >= date('now', '-7 days');")
    if [ -z "$PUNCH_COUNT" ]; then
        PUNCH_COUNT=0
    fi

    STRESS_SCORE=$(echo "scale=2; ($WEIGHT * 10) / ($DAYS_LEFT * ($PUNCH_COUNT + 1))" | bc 2>/dev/null)

    if [ -z "$STRESS_SCORE" ]; then
        STRESS_SCORE="0.00"
    fi

    IS_HIGH_RISK=$(echo "$STRESS_SCORE" | awk '{if ($1 > 5.0) print 1; else print 0;}')
    IS_MID_RISK=$(echo "$STRESS_SCORE" | awk '{if ($1 <= 5.0 && $1 > 2.0) print 1; else print 0;}')

    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

    if [ "$IS_HIGH_RISK" -eq 1 ]; then
        STATUS="[急需攻坚]"
    elif [ "$IS_MID_RISK" -eq 1 ]; then
        STATUS="[进度偏慢]"
    else
        STATUS="[状态良好]"
    fi
    echo "[$TIMESTAMP] 科目: $SUBJECT | 权重: $WEIGHT | 剩余: $DAYS_LEFT 天 | 近7天打卡: $PUNCH_COUNT 次 | 风险: $STRESS_SCORE | 评估: $STATUS"
done