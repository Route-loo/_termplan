#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

if [ -z "$1" ]; then
    echo "使用范例: $0 <data_packet.csv>"
    echo "CSV 文件标准模板样例格式: 关联用户ID,科目名称,难度权重(1-5),截止时间(YYYY-MM-DD)"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "致命错误：未能检索到指定路径下的 CSV 数据源文件。"
    exit 1
fi

echo "正在解析外部数据通道 '$1' 启动批量批量装载..."
imported_count=0

# 【高阶考核点】：通过控制内建的 IFS 域分隔符，配合 read 循环精准拆分 CSV 列
while IFS=',' read -r user_id subject weight ddl || [ -n "$user_id" ]; do
    # 规避和过滤 CSV 文件的第一行表头字段
    if [[ "$user_id" == "user_id" || -z "$subject" ]]; then
        continue
    fi

    # 过滤可能存在多余空白干扰的脏数据
    clean_user_id=$(echo "$user_id" | tr -d '[:space:]')
    clean_subject=$(echo "$subject" | tr -d '[:space:]' | sed "s/'/''/g")
    clean_weight=$(echo "$weight" | tr -d '[:space:]')
    clean_ddl=$(echo "$ddl" | tr -d '[:space:]')

    # 执行底层原子性数据注入
    sqlite3 "$DB_PATH" "INSERT INTO exams (user_id, subject, weight, ddl) VALUES ($clean_user_id, '$clean_subject', $clean_weight, '$clean_ddl');"
    if [ $? -eq 0 ]; then
        ((imported_count++))
    fi
done < "$1"

echo "注入流程终止，成功批量同步并加载 $imported_count 组备考科目节点。"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DATA-IMPORT] 批量导入成功。追加写入了 $imported_count 条新记录。" >> "$LOG_FILE"