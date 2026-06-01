#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
DB_PATH="$TERMPLAN_DIR/termplan.db"

USER_ID=${TERMPLAN_USER_ID:-0}
if [ "$USER_ID" -eq 0 ]; then
    echo "错误: 未检测到当前登录用户，请确保通过 Web 界面调用"
    exit 1
fi


echo "                   TermPlan 业务流进度综合审计报告                       "

if [ ! -f "$DB_PATH" ]; then
    echo "错误: 数据核心节点未上线，请先运行 setup.sh"
    exit 1
fi


# 直接从数据库查询当前用户的打卡汇总
sqlite3 "$DB_PATH" <<EOF
SELECT '科目: ' || subject || ' | 累计心流: ' || SUM(duration) || ' 分钟'
FROM punch_history
WHERE user_id = $USER_ID
GROUP BY subject
UNION ALL
SELECT '========================================='
UNION ALL
SELECT '总计投入 | ' || SUM(duration) || ' 分钟'
FROM punch_history
WHERE user_id = $USER_ID;
EOF
echo -e "\n========================================================================="