# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes
import database

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    # تأكد من استدعاء دالة الإضافة من قاعدة البيانات
    # سنضيف هنا المنطق الذي يمنع تعليق البوت
    await msg.reply_text("💡 جارٍ تجهيز لوحة الإضافة...")
    # ... (بقية المنطق الخاص بك)

async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    await msg.reply_text("✏️ جارٍ فتح لوحة التعديل...")
    # ... (بقية المنطق الخاص بك)
