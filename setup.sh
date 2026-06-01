#!/bin/bash

TERMPLAN_DIR="$HOME/Desktop/termplan"
LOG_FILE="$TERMPLAN_DIR/termplan.log"
DB_PATH="$TERMPLAN_DIR/termplan.db"

echo "========================================="
echo "开始部署 TermPlan..."
echo "========================================="

mkdir -p "$TERMPLAN_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "正在初始化 SQLite 数据库与标准表结构..."
    sqlite3 "$DB_PATH" <<EOF
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 3,
    ddl TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS punch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    punch_date TEXT NOT NULL,
    duration INTEGER DEFAULT 0
);
EOF
    echo "数据库全量初始化成功。"
fi

touch "$LOG_FILE"

# 自动查找当前目录下所有的 Shell 脚本并赋予执行权限
chmod +x *.sh 2>/dev/null || true
echo "基础脚本可执行控制权限配置成功。"

ZSHRC="$HOME/.zshrc"
BASHRC="$HOME/.bashrc"

for RC in "$ZSHRC" "$BASHRC"; do
    if [ -f "$RC" ] && ! grep -q "termplan motd" "$RC"; then
        echo -e "\n# TermPlan 终端环境感知自动注入\ncat $TERMPLAN_DIR/motd.txt 2>/dev/null" >> "$RC"
        echo "$RC 终端登录感知注入成功。"
    fi
done

CRON_JOB="*/30 * * * * /bin/bash $TERMPLAN_DIR/refresh_motd.sh >/dev/null 2>&1"
(crontab -l 2>/dev/null | grep -Fv "$TERMPLAN_DIR/refresh_motd.sh"; echo "$CRON_JOB") | crontab -
echo "Crontab 定时刷新任务配置成功。"

echo "========================================="
echo "TermPlan 自动化环境部署完成！"
echo "========================================="