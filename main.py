import os, json, hashlib, logging, asyncio, threading, time, requests
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MAIN_MENU, ENTER_SUBJECT, ENTER_QUIZ_NUM, QUESTION_MENU, ENTER_QUESTION_TEXT, ENTER_QUESTION_IMAGE, ENTER_ANSWER_TEXT, ENTER_ANSWER_IMAGE, CONFIRM_ADD, SELECT_QUIZ_TO_EXPORT = range(10)
DATA_FILE = "quiz_data.json"
SUBJECTS_LIST = ["مقدمة في بايثون", "رياضيات 2", "السلوك التنظيمي", "إنجليزي 2"]

def run_health_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        def log_message(self, *args): pass
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 5000))), Handler).serve_forever()

def keep_alive():
    threading.Thread(target=run_health_server, daemon=True).start()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_question_hash(text): return hashlib.md5(text.strip().lower().encode()).hexdigest()
def main_keyboard(): return ReplyKeyboardMarkup([["➕ إضافة كويز جديد", "📋 عرض الكويزات"], ["📄 تصدير PDF", "🗑 حذف كويز"]], resize_keyboard=True)

async def start(update, context):
    await update.message.reply_text("👋 *أهلاً بك في بوت جمع الكويزات!*\n\nيمكنك اختيار المادة والكويز من القوائم الجاهزة وتصديرها PDF منسق بـالعناوين.", parse_mode="Markdown", reply_markup=main_keyboard())
    return MAIN_MENU

async def new_quiz(update, context):
    context.user_data["current"] = {}
    keyboard = [[InlineKeyboardButton(sub, callback_data=f"sub__{sub}")] for sub in SUBJECTS_LIST]
    await update.message.reply_text("📚 *اختر المادة الدراسية من القائمة:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ENTER_SUBJECT

async def receive_subject_callback(update, context):
    query = update.callback_query; await query.answer()
    subject_name = query.data.replace("sub__", "")
    context.user_data["current"]["subject"] = subject_name
    keyboard = []; row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(f"كويز {i}", callback_data=f"qnum__{i}"))
        if len(row) == 3 or i == 10: keyboard.append(row); row = []
    await query.message.reply_text(f"🔢 مادة *{subject_name}*\n\n*اختر رقم الكويز من 1 إلى 10:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ENTER_QUIZ_NUM

async def receive_quiz_num_callback(update, context):
    query = update.callback_query; await query.answer()
    quiz_num = query.data.replace("qnum__", "")
    current = context.user_data["current"]; current["quiz_num"] = quiz_num
    sub = current["subject"]; quiz_key = f"{sub}__Q{quiz_num}"
    data = load_data(); u_id = str(query.from_user.id)
    if u_id not in data: data[u_id] = {}
    if quiz_key not in data[u_id]: data[u_id][quiz_key] = {"subject": sub, "quiz_num": quiz_num, "questions": [], "hashes": []}
    save_data(data); current["quiz_key"], current["user_id"] = quiz_key, u_id
    await query.message.reply_text(f"✅ تم تحديد: *{sub} - كويز {quiz_num}*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة سؤال", callback_data="add_question")]]))
    return QUESTION_MENU

async def add_question_callback(update, context):
    query = update.callback_query; await query.answer()
    context.user_data["current"]["q_tmp"] = {}
    await query.message.reply_text("✏️ *نص السؤال:*\nاكتب نص السؤال الحين:", parse_mode="Markdown")
    return ENTER_QUESTION_TEXT

async def receive_question_text(update, context):
    q_text = update.message.text.strip(); current = context.user_data["current"]
    data = load_data(); u_id, q_key = current["user_id"], current["quiz_key"]
    q_hash = get_question_hash(q_text)
    if q_hash in data[u_id][q_key]["hashes"]:
        await update.message.reply_text("⚠️ هذا السؤال تم إدخاله مسبقاً!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ سؤال جديد", callback_data="add_question")]]))
        return QUESTION_MENU
    current["q_tmp"]["text"], current["q_tmp"]["hash"] = q_text, q_hash
    await update.message.reply_text("🖼 هل تريد إضافة صورة للسؤال؟", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📷 نعم", callback_data="add_q_img")], [InlineKeyboardButton("⏭ تخطي", callback_data="skip_q_img")]]))
    return ENTER_QUESTION_IMAGE

async def add_q_img_callback(update, context):
    await update.callback_query.answer(); await update.callback_query.message.reply_text("📤 أرسل صورة السؤال:")
    return ENTER_QUESTION_IMAGE

async def receive_question_image(update, context):
    context.user_data["current"]["q_tmp"]["image_file_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("✏️ *نص الجواب:*\nاكتب الجواب الفعلي:", parse_mode="Markdown")
    return ENTER_ANSWER_TEXT

async def skip_q_img_callback(update, context):
    await update.callback_query.answer(); context.user_data["current"]["q_tmp"]["image_file_id"] = None
    await update.callback_query.message.reply_text("✏️ *نص الجواب:*\nاكتب الجواب الفعلي:", parse_mode="Markdown")
    return ENTER_ANSWER_TEXT

async def receive_answer_text(update, context):
    context.user_data["current"]["q_tmp"]["answer"] = update.message.text.strip()
    await update.message.reply_text("🖼 هل تريد إضافة صورة للجواب؟", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📷 نعم", callback_data="add_a_img")], [InlineKeyboardButton("⏭ تخطي", callback_data="skip_a_img")]]))
    return ENTER_ANSWER_IMAGE

async def add_a_img_callback(update, context):
    await update.callback_query.answer(); await update.callback_query.message.reply_text("📤 أرسل صورة الجواب:")
    return ENTER_ANSWER_IMAGE

async def receive_answer_image(update, context):
    context.user_data["current"]["q_tmp"]["answer_image_file_id"] = update.message.photo[-1].file_id
    await _confirm_q(update.message, context); return CONFIRM_ADD

async def skip_a_img_callback(update, context):
    await update.callback_query.answer(); context.user_data["current"]["q_tmp"]["answer_image_file_id"] = None
    await _confirm_q(update.callback_query.message, context); return CONFIRM_ADD

async def _confirm_q(msg, context):
    q = context.user_data["current"]["q_tmp"]
    await msg.reply_text(f"❓ *السؤال:* {q['text']}\n✅ *الجواب:* {q['answer']}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ حفظ السؤال وقفل", callback_data="save_question")]]))

async def save_question_callback(update, context):
    query = update.callback_query; await query.answer()
    current = context.user_data["current"]; q_tmp = current["q_tmp"]
    data = load_data(); u_id, q_key = current["user_id"], current["quiz_key"]
    data[u_id][q_key]["questions"].append({"text": q_tmp["text"], "image_file_id": q_tmp.get("image_file_id"), "answer": q_tmp["answer"], "answer_image_file_id": q_tmp.get("answer_image_file_id")})
    data[u_id][q_key]["hashes"].append(q_tmp["hash"]); save_data(data)
    await query.message.reply_text(f"✅ تم حفظ السؤال! المجموع: {len(data[u_id][q_key]['questions'])}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ سؤال آخر", callback_data="add_question")], [InlineKeyboardButton("📄 تصدير PDF", callback_data=f"export__{q_key}")]]))
    return QUESTION_MENU

async def list_quizzes(update, context):
    data = load_data(); u_id = str(update.effective_user.id)
    if u_id not in data or not data[u_id]: await update.message.reply_text("📭 لا توجد كويزات."); return MAIN_MENU
    txt = "📋 *الكويزات المحفوظة عندك:*\n\n"
    for k, q in data[u_id].items(): txt += f"• *{q['subject']}* - كويز {q['quiz_num']} ({len(q['questions'])} سؤال)\n"
    await update.message.reply_text(txt, parse_mode="Markdown"); return MAIN_MENU

async def export_menu(update, context):
    data = load_data(); u_id = str(update.effective_user.id)
    if u_id not in data or not data[u_id]: await update.message.reply_text("📭 لا توجد كويزات."); return MAIN_MENU
    btns = [[InlineKeyboardButton(f"📄 {q['subject']} - كويز {q['quiz_num']}", callback_data=f"export__{k}")] for k, q in data[u_id].items()]
    await update.message.reply_text("اختر الكويز للتصدير:", reply_markup=InlineKeyboardMarkup(btns))
    return SELECT_QUIZ_TO_EXPORT

async def export_quiz_callback(update, context):
    query = update.callback_query; await query.answer()
    q_key = query.data.replace("export__", ""); u_id = str(query.from_user.id); data = load_data()
    quiz = data[u_id][q_key]
    if not quiz["questions"]: await query.message.reply_text("⚠️ الكويز فارغ!"); return MAIN_MENU
    await query.message.reply_text("⏳ جاري توليد PDF...")
    await query.message.reply_document(document=BytesIO(generate_pdf(quiz, quiz["questions"])), filename=f"{quiz['subject']}_كويز_{quiz['quiz_num']}.pdf")
    return MAIN_MENU

def generate_pdf(quiz, questions):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import arabic_reshaper, urllib.request, tempfile, os as _os
    from bidi.algorithm import get_display
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not _os.path.exists(font_path):
        font_path = _os.path.join(tempfile.gettempdir(), "DejaVuSans.ttf")
        if not _os.path.exists(font_path):
            urllib.request.urlretrieve("https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf", font_path)
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    ar = lambda t: get_display(arabic_reshaper.reshape(t))
    ts = ParagraphStyle("T", fontName="DejaVuSans", fontSize=20, alignment=TA_CENTER, spaceAfter=20, leading=28)
    qs = ParagraphStyle("Q", fontName="DejaVuSans", fontSize=14, alignment=TA_RIGHT, spaceAfter=8, leading=22)
    as_ = ParagraphStyle("A", fontName="DejaVuSans", fontSize=13, alignment=TA_RIGHT, spaceAfter=15, leading=20)
    story = [Spacer(1,15), Paragraph(ar(f"{quiz['subject']} - كويز {quiz['quiz_num']}"), ts), Spacer(1,10)]
    for i, q in enumerate(questions, 1):
        story += [Paragraph(ar(f"السؤال {i}: {q['text']}"), qs), Paragraph(ar(f"الجواب: {q['answer']}"), as_), Spacer(1,5)]
    doc.build(story); return buf.getvalue()

async def delete_quiz_menu(update, context):
    data = load_data(); u_id = str(update.effective_user.id)
    if u_id not in data or not data[u_id]: await update.message.reply_text("📭 لا توجد كويزات."); return MAIN_MENU
    btns = [[InlineKeyboardButton(f"🗑 {q['subject']} - كويز {q['quiz_num']}", callback_data=f"del__{k}")] for k, q in data[u_id].items()]
    await update.message.reply_text("اختر الكويز للحذف:", reply_markup=InlineKeyboardMarkup(btns)); return MAIN_MENU

async def delete_quiz_callback(update, context):
    query = update.callback_query; await query.answer()
    k = query.data.replace("del__", ""); data = load_data(); u_id = str(query.from_user.id)
    if u_id in data and k in data[u_id]: del data[u_id][k]; save_data(data)
    await query.message.reply_text("🗑 ✅ تم الحذف."); return MAIN_MENU

async def main_menu_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("🏠 القائمة الرئيسية", reply_markup=main_keyboard()); return MAIN_MENU

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.Regex("^➕ إضافة كويز جديد$"), new_quiz), MessageHandler(filters.Regex("^📋 عرض الكويزات$"), list_quizzes), MessageHandler(filters.Regex("^📄 تصدير PDF$"), export_menu), MessageHandler(filters.Regex("^🗑 حذف كويز$"), delete_quiz_menu), CallbackQueryHandler(delete_quiz_callback, pattern="^del__"), CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"), CallbackQueryHandler(export_quiz_callback, pattern="^export__")],
            ENTER_SUBJECT: [CallbackQueryHandler(receive_subject_callback, pattern="^sub__")],
            ENTER_QUIZ_NUM: [CallbackQueryHandler(receive_quiz_num_callback, pattern="^qnum__")],
            QUESTION_MENU: [CallbackQueryHandler(add_question_callback, pattern="^add_question$"), CallbackQueryHandler(save_question_callback, pattern="^save_question$"), CallbackQueryHandler(export_quiz_callback, pattern="^export__"), CallbackQueryHandler(main_menu_callback, pattern="^main_menu$")],
            ENTER_QUESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question_text)],
            ENTER_QUESTION_IMAGE: [CallbackQueryHandler(add_q_img_callback, pattern="^add_q_img$"), CallbackQueryHandler(skip_q_img_callback, pattern="^skip_q_img$"), MessageHandler(filters.PHOTO, receive_question_image)],
            ENTER_ANSWER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer_text)],
            ENTER_ANSWER_IMAGE: [CallbackQueryHandler(add_a_img_callback, pattern="^add_a_img$"), CallbackQueryHandler(skip_a_img_callback, pattern="^skip_a_img$"), MessageHandler(filters.PHOTO, receive_answer_image)],
            CONFIRM_ADD: [CallbackQueryHandler(save_question_callback, pattern="^save_question$"), CallbackQueryHandler(add_question_callback, pattern="^add_question$"), CallbackQueryHandler(main_menu_callback, pattern="^main_menu$")],
            SELECT_QUIZ_TO_EXPORT: [CallbackQueryHandler(export_quiz_callback, pattern="^export__"), CallbackQueryHandler(main_menu_callback, pattern="^main_menu$")],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    app.add_handler(conv); keep_alive(); app.run_polling()

if __name__ == "__main__":
    main()
