import os
import sqlite3

DB_PATH = os.path.expanduser("~/Desktop/termplan/termplan.db")

def local_fallback_engine():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT subject, weight, ddl, CAST((julianday(ddl) - julianday('now', 'localtime')) AS INT) FROM exams")
    exams = cursor.fetchall()
    
    cursor.execute("SELECT subject, COUNT(*) FROM punch_history WHERE punch_date >= date('now', '-7 days') GROUP BY subject")
    punches = dict(cursor.fetchall())
    conn.close()

    if not exams:
        return "  💡 暂无科目。"

    suggestions = []
    for exam in exams:
        sub, weight, ddl, days_left = exam
        days_left = max(1, days_left)
        recent_punch = punches.get(sub, 0)
        
        stress_score = (weight * 10) / (days_left * (recent_punch + 1))
        if stress_score > 5.0:
            suggestions.append(f"  ⚠️  \033[1;31m{sub}\033[0m 挂科预警！剩余 {days_left} 天，近一周仅打卡 {recent_punch} 次。")
        elif stress_score > 2.0:
            suggestions.append(f"   {sub} 进度偏慢，建议保持每天打卡。")
        else:
            suggestions.append(f"   {sub} 状态良好，继续保持。")
            
    return "\n".join(suggestions)

if __name__ == "__main__":
    print(local_fallback_engine())