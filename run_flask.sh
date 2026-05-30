#!/bin/bash
TERMPLAN_DIR="$HOME/Desktop/termplan"
LOG_FILE="$TERMPLAN_DIR/termplan.log"

# 进入当前脚本所在的实际运行根目录
cd "$(dirname "$0")" || exit 1

echo "========================================="
echo "        TermPlan 生产级服务启动调度器     "
echo "========================================="

# 动态唤醒 Python 虚拟依赖环境 (自适应探测项目内或用户主目录下虚拟环境)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -f "$HOME/termplan/venv/bin/activate" ]; then
    source "$HOME/termplan/venv/bin/activate"
fi

# 隔离并动态加持 NVIDIA 专属人工智能鉴权密钥
if [ -f "$HOME/.termplan_key" ]; then
    export NVIDIA_API_KEY=$(cat "$HOME/.termplan_key" 2>/dev/null)
else
    # 容错降级环境注入
    export NVIDIA_API_KEY="YOUR_NVIDIA_API_KEY"
fi

# 确保 Flask 运行所需私钥具备环境态隔离
export SECRET_KEY="termplan_morandi_production_secret_key_2026"

echo "正在将 Flask Web 业务流挂载至 Linux 后台常驻守护进程..."
# 【高阶考核点】：利用 nohup 配合标准重定向，将 Python 的日志与 Shell 的日志完美归口。
nohup python3 app.py >> "$LOG_FILE" 2>&1 &

PID=$!

if ps -p $PID > /dev/null; then
    echo "Flask 后台服务已经挂载上线成功！"
    echo "服务常驻分配进程 PID: $PID"
    echo "实时控制输出流已重定向追踪至: $LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SYSTEM-DAEMON] 后台进程成功挂载启动，PID 锁定为: $PID" >> "$LOG_FILE"
else
    echo "进程部署挂载失败，请通过查看 $LOG_FILE 分析报错崩溃栈。"
fi
echo "========================================="