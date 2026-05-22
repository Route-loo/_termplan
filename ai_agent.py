import os
import sqlite3
from openai import OpenAI


DB_PATH = os.path.expanduser("~/Desktop/termplan/termplan.db")


NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY")


def get_db_context():
   
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

       
        cursor.execute("""
            SELECT subject, weight, ddl, 
            CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) 
            FROM exams
        """)
        exams = cursor.fetchall()

        
        cursor.execute("""
            SELECT subject, COUNT(*) 
            FROM punch_history 
            WHERE punch_date >= date('now', '-7 days') 
            GROUP BY subject
        """)
        punches = dict(cursor.fetchall())
        conn.close()

        if not exams:
            return "该学生目前没有规划任何期末考试科目，状态比较轻松。"

       
        context_lines = []
        for exam in exams:
            sub, weight, ddl, days_left = exam
            days_left = max(0, days_left)
            recent_punch = punches.get(sub, 0)

            
            stress_score = (weight * 10) / (max(1, days_left) * (recent_punch + 1))
            status = "极度危险/急需攻坚" if stress_score > 5.0 else (
                "进度偏慢" if stress_score > 2.0 else "节奏良好")

            context_lines.append(
                f"- 科目: {sub} | 权重(难度): {weight} | 距离考试剩 {days_left} 天 | 近一周心流打卡: {recent_punch} 次 | 当前评估: {status}"
            )

        return "\n".join(context_lines)

    except Exception as e:
        return f"（系统提示：暂时无法读取本地复习数据，原因：{str(e)}）"


def call_nvidia_ai(user_message):
   
    if not NVIDIA_API_KEY or NVIDIA_API_KEY == "YOUR_NVIDIA_API_KEY":
        return "顾问提示：检测到您的后端尚未配置 NVIDIA_API_KEY，请检查环境部署。"

   
    student_context = get_db_context()

   
    system_prompt = (
        "你是一个集成在极简复习软件 'TermPlan' 中的自适应 AI 顾问。\n"
        "你的主要职责是根据学生当下的情绪/困惑，结合其后台真实的复习进度，提供温柔、平和、具有安抚感且切实可行的排程和复习建议。\n"
        "【请遵守以下语气与人设规范】：\n"
        "1. 你的说话风格应像莫兰迪色系一样偏向静谧、沉稳、解压，多用‘轻轻放下’、‘理清步调’、‘建立节奏流’等温和词汇，严禁敷衍，严禁使用过于生硬、高高在上的说教口吻。\n"
        "2. 不要主动提及数据库、代码或底层逻辑，要将数据自然地融入到你的关怀和备考建议中。\n\n"
        f"【当前学生的真实备考数据流如下】:\n{student_context}\n\n"
        "请根据上述数据和用户的发言，给出一共不超过 250 字的精致回复。"
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
                {"role": "user", "content": user_message}
            ],
            temperature=0.6, 
            max_tokens=512,
            top_p=1,
            stream=False
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        return f"顾问在冥想中开小差了（API 调用失败）: {str(e)}"


if __name__ == "__main__":
 
    print("正在测试 NVIDIA 大模型调用...")
    test_response = call_nvidia_ai("我觉得那个 Linux 考查课好烦啊，根本不想复习，怎么办？")
    print(f"\n[AI 顾问回复]:\n{test_response}")