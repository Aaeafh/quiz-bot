# -*- coding: utf-8 -*-
import sqlite3
import os

# السر هنا: نحدد مسار قاعدة البيانات بناءً على مكان وجود الملف الحالي
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_bank.db")

def get_connection():
    # نفتح الاتصال دائماً بالمسار الصحيح
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # إنشاء الجداول الأساسية إذا لم تكن موجودة
    c.execute("CREATE TABLE IF NOT EXISTS sections (id INTEGER PRIMARY KEY, name TEXT, chat_id INTEGER, thread_id INTEGER, user_id INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, section_id INTEGER, quiz_num INTEGER, user_id INTEGER, question_text TEXT, answer_text TEXT, question_image TEXT, answer_image TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (user_id INTEGER PRIMARY KEY, chat_id INTEGER, thread_id INTEGER, state TEXT, section_id INTEGER, draft_q_id INTEGER, base_msg_id INTEGER)")
    conn.commit()
    conn.close()

# ... (بقية الدوال الخاصة بك: get_section, upsert_section, إلخ)
# تأكد من استخدام get_connection() في كل دالة بدلاً من sqlite3.connect مباشرة
