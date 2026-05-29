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


def init_business_tables():
   
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,         
            subject TEXT NOT NULL,
            weight INTEGER DEFAULT 3,
            ddl TEXT NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS punch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            punch_date TEXT NOT NULL,
            duration INTEGER DEFAULT 30
        );
    """)
    
    conn.commit()
    conn.close()


@app.route("/login")
def login_page():
    
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
    init_business_tables()

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
            session["user_id"] = user[0]
            return jsonify({"status": "success", "msg": "登录成功"})
        else:
            return jsonify({"status": "error", "msg": "用户名或密码错误，请重试"})

    return jsonify({"status": "error", "msg": "未知的操作指令"})


@app.route("/")
def index():
    if "user" not in session or "user_id" not in session:
        return redirect(url_for("login_page"))

    current_user_id = session["user_id"]
    
    auth.init_db()
    init_business_tables()
    
    conn = get_db_connection()
    
   
    exams = conn.execute(
        """SELECT subject, weight, ddl, 
           CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left 
           FROM exams WHERE user_id = ? ORDER BY ddl ASC""", (current_user_id,)
    ).fetchall()

    logs = conn.execute(
        """SELECT punch_date, SUM(duration) as total 
           FROM punch_history WHERE user_id = ? AND punch_date >= date('now', '-30 days') 
           GROUP BY punch_date""", (current_user_id,)
    ).fetchall()

    total_minutes = (
        conn.execute("SELECT SUM(duration) FROM punch_history WHERE user_id = ?", (current_user_id,)).fetchone()[0]
        or 0
    )
    total_exams = (
        conn.execute("SELECT COUNT(*) FROM exams WHERE user_id = ?", (current_user_id,)).fetchone()[0] or 0
    )
    most_active = conn.execute(
        """SELECT subject FROM punch_history WHERE user_id = ? 
           GROUP BY subject ORDER BY SUM(duration) DESC LIMIT 1""", (current_user_id,)
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
    session.clear() 
    return redirect(url_for("login_page"))



@app.route("/api/add", methods=["POST"])
def add_exam():
    if "user_id" not in session:
        return jsonify({"status": "error", "msg": "会话鉴权失效，请重新登录"})

    data = request.json
    print("--- 后端收到前端部署请求数据 ---:", data)

    subject = data.get("subject", "").strip() if data.get("subject") else ""
    
    try:
        weight = int(data.get("weight", 3))
    except (ValueError, TypeError):
        weight = 3
        
    ddl = data.get("ddl")
    current_user_id = session["user_id"]

    if not subject or not ddl:
        return jsonify({"status": "error", "msg": "核心字段溢出：科目与日期不可为空"})

    try:
        conn = get_db_connection()
        
        conn.execute(
            "INSERT OR IGNORE INTO exams (user_id, subject, weight, ddl) VALUES (?, ?, ?, ?)",
            (current_user_id, subject, weight, ddl),
        )
        conn.commit()
        conn.close()
        
        print(f"--- 注入状态同步成功 ---: 用户 {current_user_id} 成功部署科目 [{subject}]")
        return jsonify(
            {
                "status": "success",
                "msg": f" 目标科目 [{subject}] 已成功注入您的控制矩阵！",
            }
        )
    except Exception as e:
        print("--- 数据库写入失败底层报错 ---:", str(e))
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/del", methods=["POST"])
def del_exam():
    if "user_id" not in session:
        return jsonify({"status": "error", "msg": "会话鉴权失效，请重新登录"})

    data = request.json
    subject = data.get("subject")
    current_user_id = session["user_id"]
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM exams WHERE user_id=? AND subject=?", (current_user_id, subject))
        conn.commit()
        conn.close()
        return jsonify(
            {
                "status": "success",
                "msg": f"已将科目 [{subject}] 从您的监测域中安全抹除。",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/api/punch", methods=["POST"])
def punch():
    if "user_id" not in session:
        return jsonify({"status": "error", "msg": "会话鉴权失效，请重新登录"})

    data = request.json
    subject = data.get("subject")
    duration = int(data.get("duration", 30))
    today = datetime.now().strftime("%Y-%m-%d")
    current_user_id = session["user_id"]

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO punch_history (user_id, subject, punch_date, duration) VALUES (?, ?, ?, ?)",
            (current_user_id, subject, today, duration),
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
    if "user_id" not in session:
        return jsonify({"status": "error", "msg": "顾问无法识别您的会话节点，请先登录"})

    data = request.json
    user_msg = data.get("message", "").strip()
    current_user_id = session["user_id"]

    if not user_msg:
        return jsonify({"status": "error", "msg": "写下的困惑不能为空白哦"})

    try:
        conn = get_db_connection()
        exams = conn.execute(
            "SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) as days_left FROM exams WHERE user_id = ?", (current_user_id,)
        ).fetchall()
        punches = conn.execute(
            "SELECT subject, COUNT(*) as cnt FROM punch_history WHERE user_id = ? AND punch_date >= date('now', '-7 days') GROUP BY subject", (current_user_id,)
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
    init_business_tables() 
    app.run(debug=True, port=5000)