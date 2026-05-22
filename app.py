import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from openai import OpenAI
import auth

app = Flask(__name__)

app.secret_key = "termplan_morandi_secret_key"

DB_PATH = "D:\\termplan\\termplan.db"

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/login")
def login_page():
    """当直接访问 /login 时，优雅展现你设计的 HTML 登录卡片"""
    return render_template("login.html")



@app.route("/api/auth", methods=["POST"])
def auth_api():
    
    data = request.json
    action = data.get("action")      
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"status": "error", "msg": "用户名或密码不能为空"})

   
    auth.init_db()

    if action == "register":
       
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        pwd_hash = auth.hash_password(password)
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pwd_hash))
            conn.commit()
            return jsonify({"status": "success", "msg": "恭喜，节点部署成功！切回登录端试试吧。"})
        except sqlite3.IntegrityError:
            return jsonify({"status": "error", "msg": "该用户名已被注册，请换一个"})
        finally:
            conn.close()

    elif action == "login":
       
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        pwd_hash = auth.hash_password(password)
        cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, pwd_hash))
        user = cursor.fetchone()
        conn.close()

        if user:
           
            session["user"] = username
            return jsonify({"status": "success", "msg": "登录成功"})
        else:
            return jsonify({"status": "error", "msg": "用户名或密码错误，请重试"})

    return jsonify({"status": "error", "msg": "未知的操作指令"})



@app.route("/")
def index():
    
    if "user" not in session:
        return redirect(url_for("login_page"))

   
    auth.init_db()
    
    conn = get_db_connection()
    
    exams = conn.execute(
        "SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left FROM exams ORDER BY ddl ASC"
    ).fetchall()

   
    logs = conn.execute(
        "SELECT punch_date, SUM(duration) as total FROM punch_history WHERE punch_date >= date('now', '-30 days') GROUP BY punch_date"
    ).fetchall()

   
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

   
    heatmap_data = {log["punch_date"]: log["total"] for log in logs}
    today = datetime.now()
    past_30_days = []
    for i in range(29, -1, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        mins = heatmap_data.get(date_str, 0)
       
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
        username=session["user"] 
    )



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


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
                "msg": f" 目标科目 [{subject}] 已成功注入控制矩阵！",
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
                "msg": f"已将科目 [{subject}] 从监测域中安全抹除。",
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

       
        if os.name != 'nt':
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



@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"status": "error", "msg": "写下的困惑不能为空白哦"})

    try:
        conn = get_db_connection()
        exams = conn.execute(
            "SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left FROM exams"
        ).fetchall()
        punches = conn.execute(
            "SELECT subject, COUNT(*) as cnt FROM punch_history WHERE punch_date >= date('now', '-7 days') GROUP BY subject"
        ).fetchall()
        conn.close()

        punch_dict = {p["subject"]: p["cnt"] for p in punches}
    except Exception as e:
        exams, punch_dict = [], {}

    context_lines = []
    for e in exams:
        sub = e["subject"]
        days = max(0, e["days_left"])
        recent = punch_dict.get(sub, 0)
        weight = e["weight"]
        stress = (weight * 10) / (max(1, days) * (recent + 1))
        status = " 极度危险/急需攻坚" if stress > 5.0 else (" 进度偏慢" if stress > 2.0 else " 节奏良好")
        context_lines.append(
            f"- 科目: {sub} | 难度权重: {weight} | 距离考试剩 {days} 天 | 近一周心流打卡: {recent} 次 | 状态评估: {status}"
        )

    student_context = "\n".join(context_lines) if context_lines else "目前大盘很整洁，没有部署任何期末考试科目。"

    if not NVIDIA_API_KEY:
        return jsonify({
            "status": "success",
            "reply": "顾问提示：检测到您的后端尚未检测到环境变量 NVIDIA_API_KEY。请在终端执行相关配置后再启动本系统。"
        })

    system_prompt = (
        "你是一个集成在极简复习软件 'TermPlan' 中的自适应 AI 顾问。\n"
        "你的职责是根据学生当下的情绪/困惑，结合其后台真实的复习进度，提供温柔、平和、具有安抚感且切实可行的排程和复习建议。\n"
        "【请遵守以下语气与人设规范】：\n"
        "1. 你的说话风格应像莫兰迪色系一样偏向静谧、沉稳、解压，多用‘轻轻放下’、‘理清步调’、‘建立节奏流’等温和词汇，严禁机械敷衍，严禁使用傲慢的说教口吻。\n"
        "2. 不要主动在对话里提及‘数据库’、‘代码’或‘底层逻辑’等词汇，要将数据不动声色地融进你的关怀和备考建议中。\n\n"
        f"【当前学生的真实备考数据流如下】:\n{student_context}\n\n"
        "请根据上述数据流和用户的发言，给出一共不超过 250 字的精致回复。"
    )

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_API_KEY
        )
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.6,
            max_tokens=512,
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = f"顾问在冥想中开小差了（API 调用失败）: {str(e)}"

    return jsonify({"status": "success", "reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)