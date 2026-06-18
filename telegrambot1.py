import os
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# 1. បង្កើត Web Server ក្លែងក្លាយសម្រាប់ Render Free Plan
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# កំណត់ដំណាក់កាលនៃ Conversation
NAME, PHONE, PRODUCT, LOCATION, CONFIRM = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🛍️ ធ្វើការកម្មង់ (Order)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("សួស្តី! សូមចុចប៊ូតុងខាងក្រោមដើម្បីចាប់ផ្តើមទិញទំនិញ៖", reply_markup=reply_markup)

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("សូមបញ្ចូលឈ្មោះរបស់អ្នក:", reply_markup=ReplyKeyboardRemove())
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("សូមបញ្ចូលលេខទូរស័ព្ទរបស់អ្នក:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("សូមបញ្ចូលទំនិញដែលអ្នកចង់ទិញ:")
    return PRODUCT

async def get_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["product"] = update.message.text
    instruction_text = (
        "📍 សូមផ្ញើទីតាំងដែលអ្នកចង់ឱ្យយើងដឹកទៅ៖\n\n"
        "👉 របៀបដៅទីតាំងផ្សេងៗដោយខ្លួនឯង៖\n"
        "1. ចុចលើសញ្ញា 📎 (Paperclip) នៅប្រអប់សរសេរសារខាងក្រោម\n"
        "2. ជ្រើសរើសយកពាក្យ 'Location'\n"
        "3. អ្នកអាចអូសផែនទីស្វែងរកផ្ទះ ឬកន្លែងផ្សេងទៀតដែលចង់ឱ្យដឹកទៅ\n"
        "4. រួចចុចលើពាក្យ 'Send This Location'"
    )
    await update.message.reply_text(instruction_text)
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        context.user_data["lat"] = update.message.location.latitude
        context.user_data["lng"] = update.message.location.longitude
        name = context.user_data.get("name")
        phone = context.user_data.get("phone")
        product = context.user_data.get("product")
        
        summary = (
            f"📋 សូមពិនិត្យព័ត៌មានកុម្មង់របស់អ្នក៖\n\n"
            f"👤 ឈ្មោះ: {name}\n"
            f"📞 លេខទូរស័ព្ទ: {phone}\n"
            f"🛍️ ទំនិញ: {product}\n"
            f"📍 ទីតាំងដឹកជញ្ជូន: បានដៅលើផែនទីរួចរាល់\n\n"
            f"តើព័ត៌មានខាងលើនេះត្រឹមត្រូវហើយឬនៅ?"
        )
        keyboard = [["✅ ត្រឹមត្រូវ (បញ្ជូនការកម្មង់)", "❌ បោះបង់ការកម្មង់"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(summary, reply_markup=reply_markup)
        return CONFIRM
    else:
        await update.message.reply_text("⚠️ សូមចុចលើសញ្ញា 📎 រួចរើសយក 'Location' ដើម្បីដៅទីតាំងផ្ញើមក។")
        return LOCATION

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("name")
    phone = context.user_data.get("phone")
    product = context.user_data.get("product")
    lat = context.user_data.get("lat")
    lng = context.user_data.get("lng")
    
    google_maps_link = f"https://www.google.com/maps?q={lat},{lng}"
    admin_chat_id = 8106319260  
    
    try:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"🔔 [Order ថ្មី]\n👤 ឈ្មោះ: {name}\n📞 លេខទូរស័ព្ទ: {phone}\n🛍️ ទំនិញ: {product}\n📍 ផែនទី: {google_maps_link}"
        )
        await context.bot.send_location(chat_id=admin_chat_id, latitude=lat, longitude=lng)
    except Exception as e:
        print(f"Error admin: {e}")
        
    keyboard = [["🛍️ ធ្វើការកម្មង់ (Order)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("✅ ការកម្មង់របស់អ្នកត្រូវបានបញ្ជូនរួចរាល់ហើយ!", reply_markup=reply_markup)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🛍️ ធ្វើការកម្មង់ (Order)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("❌ ការកម្មង់ត្រូវបានបោះបង់ចោល។", reply_markup=reply_markup)
    return ConversationHandler.END

def main():
    # ⚠️ យក Token ថ្មីស្រឡាងដែលទើប Revoke មុននេះមកផាសដាក់ជំនួសត្រង់នេះ
    TOKEN = "8338881319:AAFDpQzazdm6NZiLBrK2l_L9TM3A4ApmicI"
    
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("order", order),
            MessageHandler(filters.Regex(r"^🛍️ ធ្វើការកម្មង់ \(Order\)$"), order)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product)],
            LOCATION: [
                MessageHandler(filters.LOCATION, get_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)
            ],
            CONFIRM: [MessageHandler(filters.Regex(r"^✅ ត្រឹមត្រូវ"), confirm_order)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^❌ បោះបង់ការកម្មង់$"), cancel)
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("Bot is starting...")
    # ប្រើ drop_pending_updates=True ដើម្បីកាត់ផ្តាច់ Conflict ចោលទាំងអស់ពេលបើកដំបូង
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
