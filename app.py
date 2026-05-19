# app.py
import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.path.expanduser("~/Desktop/termplan/termplan.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    conn = get_db_connection()
    # 1. 获取核心考期监控数据
    exams = conn.execute(
        "SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left FROM exams ORDER BY ddl ASC"
    ).fetchall()

    # 2. 获取近 30 天的打卡总时长
    logs = conn.execute(
        "SELECT punch_date, SUM(duration) as total FROM punch_history WHERE punch_date >= date('now', '-30 days') GROUP BY punch_date"
    ).fetchall()

    # 3. 计算极客数据中心高维指标
    total_minutes = (
        conn.execute("SELECT SUM(duration) FROM punch_history").fetchone()[0]
        or 0
    )
    total_exams = (
        conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0] or 0
    )
    most_active = conn.execute(
        "SELECT subject FROM punch_history GROUP BY subject ORDER BY SUM(duration) DESC LIMIT 1"
    ).fetchone()
    most_active_sub = most_active[0] if most_active else "暂无数据"

    conn.close()

    # 4. 构建精准匹配的30天时间序列热力图矩阵
    heatmap_data = {log["punch_date"]: log["total"] for log in logs}
    today = datetime.now()
    past_30_days = []
    for i in range(29, -1, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        mins = heatmap_data.get(date_str, 0)
        # 映射热力图颜色等级 (0-3)
        level = 0
        if mins > 0 and mins <= 30:
            level = 1
        elif mins > 30 and mins <= 60:
            level = 2
        elif mins > 60:
            level = 3
        past_30_days.append(
            {"date": date_str, "duration": mins, "level": level}
        )

    return render_template(
        "index.html",
        exams=exams,
        past_30_days=past_30_days,
        stats={
            "total_minutes": total_minutes,
            "total_exams": total_exams,
            "most_active": most_active_sub,
        },
    )


@app.route("/api/add", methods=["POST"])
def add_exam():
    data = request.json
    subject = data.get("subject", "").strip()
    weight = int(data.get("weight", 3))
    ddl = data.get("ddl")

    if not subject or not ddl:
        return jsonify({"status": "error", "msg": "核心字段溢出：科目与日期不可为空"})

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO exams (subject, weight, ddl) VALUES (?, ?, ?)",
            (subject, weight, ddl),
        )
        conn.commit()
        conn.close()
        return jsonify(
            {
                "status": "success",
                "msg": f"☄️ 目标科目 [{subject}] 已成功注入控制矩阵！",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/del", methods=["POST"])
def del_exam():
    data = request.json
    subject = data.get("subject")
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM exams WHERE subject=?", (subject,))
        conn.commit()
        conn.close()
        return jsonify(
            {
                "status": "success",
                "msg": f" 已将科目 [{subject}] 从监测域中安全抹除。",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/punch", methods=["POST"])
def punch():
    data = request.json
    subject = data.get("subject")
    duration = int(data.get("duration", 30))
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO punch_history (subject, punch_date, duration) VALUES (?, ?, ?)",
            (subject, today, duration),
        )
        conn.commit()
        conn.close()

        # 联动原生环境通知
        os.system(
            f"osascript -e 'display notification \"打卡记录：{subject} +{duration}min\" with title \"⚡️ TermPlan 状态同步成功\"'"
        )
        return jsonify(
            {
                "status": "success",
                "msg": f" 能量注入成功！{subject} 递增 {duration} 分钟。",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


# --- AI 备考心理疏导对话引擎 ---
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()

    conn = get_db_connection()
    exams = conn.execute(
        "SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left FROM exams"
    ).fetchall()
    punches = conn.execute(
        "SELECT subject, COUNT(*) FROM punch_history WHERE punch_date >= date('now', '-7 days') GROUP BY subject"
    ).fetchall()
    conn.close()

    punch_dict = {p[0]: p[1] for p in punches}

    # 动态分析计算目前压力载荷最高的科目（压迫指数 = 权重 * 10 / (剩余天数 * 打卡率)）
    urgent_sub, max_stress = None, -1
    for e in exams:
        days = max(1, e["days_left"])
        recent = punch_dict.get(e["subject"], 0)
        stress = (e["weight"] * 10) / (days * (recent + 1))
        if stress > max_stress:
            max_stress = stress
            urgent_sub = {"name": e["subject"], "days": days, "cnt": recent}

    # 上下文感知与智能化情绪应答逻辑
    if (
        "焦虑" in user_msg
        or "压力" in user_msg
        or "学不完" in user_msg
        or "慌" in user_msg
    ):
        if urgent_sub:
            reply = f"检测到你的心理波形由于【{urgent_sub['name']}】出现严重扰动。当前该科目考期仅剩 {urgent_sub['days']} 天，近一周量化打卡仅 {urgent_sub['cnt']} 次。请注意，焦虑是高级智力对未知危机的防御机制。现在听我指令：切断一切外部高熵干扰，进入控制台启动一个 25 分钟的无扰打卡。行动是重构崩溃秩序的唯一解药。"
        else:
            reply = "当前外部监控集群显示并无极端倒计时威胁。备考期间的心理波动属于正常的认知过载。建议执行一个‘线程挂起’操作：离开座位，深呼吸，去喝杯水。你的底层架构非常优秀，允许存在 Warning，但不必让它演变成 Fatal Error。"
    elif "规划" in user_msg or "怎么复习" in user_msg or "建议" in user_msg:
        if urgent_sub:
            reply = f"【系统智能排程推荐】：建议立刻将 70% 的计算资源向【{urgent_sub['name']}】倾斜。由于其剩余天数短且近期活跃度低下，当前处于红区载荷状态。推荐策略：摒弃大块复习幻想，拆解成 3 个 20 分钟的小型进程流，在左侧控制台分步打卡，拉平风险曲线。"
        else:
            reply = "当前各科目负载均衡，系统运行良好。建议采用‘时间片轮转算法’：每门科目依次无扰打卡 30 分钟，保持全科神经元的整体活跃度，避免单一科目长期挂起。"
    else:
        if urgent_sub:
            reply = f"信号已接收。我一直在后台维护你的备考数据流，目前看【{urgent_sub['name']}】的压迫指数最高。无论你遇到了技术瓶颈还是情绪低谷，都可以在这里随时向我呼叫。需要现在为【{urgent_sub['name']}】开启一轮专注打卡吗？"
        else:
            reply = "AI 心理调度终端处于就绪状态，未检测到极端异常。你可以向我咨询复习规划，或者在这里倾诉备考中的负面情绪。系统随时为你提供高弹性的策略缓冲。"

    return jsonify({"status": "success", "reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)