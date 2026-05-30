#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

clear
echo "========================================================================="
echo "                   TermPlan 业务流进度综合审计报告                       "
echo "========================================================================="

if [ ! -f "$DB_PATH" ]; then
    echo "错误: 数据核心节点未上线，请先运行 setup.sh"
    exit 1
fi

echo -e "\n[板块 2: AWK 心流打卡热力感知系统]"
if [ -f "$LOG_FILE" ] && [ -s "$LOG_FILE" ]; then
    awk -F'[ =]' '
    /PUNCH/ {
        for(i=1; i<=NF; i++) {
            if($i == "SUBJECT") sub_name=$(i+1);
            if($i == "DURATION") dur=$(i+1);
        }
        stats[sub_name] += dur;
        total += dur;
    }
    END {
        # 同样去掉复杂的 printf，直接用 | 隔开
        print "科目名称 | 累计心流(分钟)"
        for(s in stats) {
            print s " | " stats[s]
        }
        print "总计投入 | " total
    }' "$LOG_FILE"
else
    echo "提示: 当前系统日志流水线为空，暂无心流打卡数据可供分析。"
fi
echo -e "\n========================================================================="