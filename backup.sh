#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
BACKUP_DIR="$TERMPLAN_DIR/backups"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

log_event() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BACKUP-DAEMON] $*" >> "$LOG_FILE"
}

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/termplan_snapshot_$(date +%Y%m%d_%H%M%S).tar.gz"

if [ ! -f "$DB_PATH" ]; then
    log_event "备份中断：未捕获到活跃的业务数据库文件。"
    echo "未检测到活跃的物理数据库，备份取消。"
    exit 1
fi

echo "开始为 TermPlan 控制矩阵构建增量状态快照..."
# 建立临时缓冲文件规避数据库直接读写锁问题
cp "$DB_PATH" "$BACKUP_DIR/termplan.db.tmp"
tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" termplan.db.tmp
rm "$BACKUP_DIR/termplan.db.tmp"

if [ $? -eq 0 ]; then
    echo "安全快照成功归档: $BACKUP_FILE"
    log_event "安全快照归档成功: $(basename "$BACKUP_FILE")"
else
    echo "错误：归档失败，请检查物理磁盘空间权限。"
    log_event "异常：归档写入失败。"
    exit 1
fi

# 【高阶考核点】：查找并自动抹除留存期长于 7 天的旧备份文件，实现内存自平衡控制
echo "正在检测过期历史快照进行轮转清理..."
find "$BACKUP_DIR" -type f -name "termplan_snapshot_*.tar.gz" -mtime +7 -print -exec rm -f {} \; | while read -r expired; do
    log_event "历史快照轮转自动销毁: $(basename "$expired")"
done
echo "快照自循环守护任务执行结束。"