#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
OUTPUT_MOTD="$TERMPLAN_DIR/motd.txt"

CLOSEST_EXAM=$(sqlite3 "$DB_PATH" "SELECT subject, CAST(julianday(ddl) - julianday('now', 'localtime') AS INT) FROM exams WHERE ddl >= date('now', 'localtime') ORDER BY ddl ASC LIMIT 1;")

if [ -z "$CLOSEST_EXAM" ]; then
    echo -e "\033[1;32m[TermPlan] 暂无近期考试任务 \033[0m" > "$OUTPUT_MOTD"
    exit 0
fi

IFS="|" read -r SUBJECT DAYS_LEFT <<< "$CLOSEST_EXAM"

{
    echo -e "\033[1;31m"
    echo "  _____                     ____  _an "
    echo " |_   _|__ _ __ _ __ ___  |  _ \| | __ _ _ __  "
    echo "   | |/ _ \ '__| '_ \` _ \ | |_) | |/ _\` | '_ \ "
    echo "   | |  __/ |  | | | | | ||  __/| | (_| | | | |"
    echo "   |_|\___|_|  |_| |_| |_||_|   |_|\__,_|_| |_|"
    echo -e "\033[0m"
    echo "========================================================="
    echo -e "  警报: 距离 [\033[1;33m $SUBJECT \033[0m] 考试仅剩 \033[1;31m $DAYS_LEFT \033[0m 天！"
    echo "========================================================="
} > "$OUTPUT_MOTD"