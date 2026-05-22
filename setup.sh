

TERMPLAN_DIR="$HOME/Desktop/termplan"
LOG_FILE="$TERMPLAN_DIR/termplan.log"
DB_PATH="$TERMPLAN_DIR/termplan.db"

echo "========================================="
echo "开始部署 TermPlan..."
echo "========================================="


if [ ! -f "$DB_PATH" ]; then
    echo "正在初始化 SQLite 数据库..."
    sqlite3 "$DB_PATH" <<EOF
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL UNIQUE,
    weight INTEGER NOT NULL,
    ddl TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS punch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    punch_date TEXT NOT NULL,
    duration INTEGER DEFAULT 0
);
EOF
    echo "数据库初始化成功。"
fi


touch "$LOG_FILE"


ZSHRC="$HOME/.zshrc"
if ! grep -q "termplan motd" "$ZSHRC"; then
    echo -e "\n# TermPlan 终端环境感知自动注入\ncat $TERMPLAN_DIR/motd.txt 2>/dev/null" >> "$ZSHRC"
    echo ".zshrc 终端登录感知注入成功。"
fi


CRON_JOB="*/30 * * * * /bin/bash $TERMPLAN_DIR/refresh_motd.sh >/dev/null 2>&1"
(crontab -l 2>/dev/null | grep -Fv "$TERMPLAN_DIR/refresh_motd.sh"; echo "$CRON_JOB") | crontab -
echo "Crontab 定时刷新任务配置成功。"

echo "部署完成！"