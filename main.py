# -*- coding: utf-8 -*-
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database
import main_logic

def main():
    # هذا هو الكود الأساسي الذي يشغل كل شيء
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # ربط الأوامر من ملف main_logic
    app.add_handler(CommandHandler("start", main_logic.cmd_start))
    app.add_handler(CommandHandler("set", main_logic.cmd_set))
    app.add_handler(CommandHandler("add", main_logic.cmd_add))
    app.add_handler(CommandHandler("edit", main_logic.cmd_edit))
    app.add_handler(CommandHandler("show", main_logic.cmd_show))
    app.add_handler(CommandHandler("panel", main_logic.cmd_panel))
    
    # ربط الأزرار والرسائل
    app.add_handler(CallbackQueryHandler(main_logic.cb_global_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, main_logic.msg_handler))
    
    print("🚀 البوت يعمل!")
    app.run_polling()

if __name__ == "__main__":
    database.init_db()
    main()
