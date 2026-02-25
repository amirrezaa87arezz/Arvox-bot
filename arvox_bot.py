import telebot
from telebot import types
import requests
import json
import os
import time
from datetime import datetime

# تنظیمات ربات - دریافت از محیط Railway
TOKEN = os.environ.get('TELEGRAM_TOKEN')
API_KEY = os.environ.get('GROQ_API_KEY')
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# بررسی وجود توکن‌ها
if not TOKEN or not API_KEY:
    raise ValueError("لطفاً توکن‌های مورد نیاز را در محیط تنظیم کنید!")

# ایجاد نمونه ربات
bot = telebot.TeleBot(TOKEN)

# بقیه کد مانند قبل (از اینجا به بعد)
user_conversations = {}

AVAILABLE_MODELS = {
    "llama3-70b": "Llama 3 (پیشرفته)",
    "llama3-8b": "Llama 3 (سریع)",
    "mixtral-8x7b": "Mixtral (متوسط)",
    "gemma-7b": "Gemma (سبک)"
}

WELCOME_MESSAGE = """
🤖 به ربات **Arvox** خوش آمدید!

من یک دستیار هوش مصنوعی هستم که می‌توانم به سوالات شما پاسخ دهم.
از مدل Llama 3 برای پاسخگویی استفاده می‌کنم.

**قابلیت‌ها:**
✅ پاسخ به سوالات عمومی
✅ مکالمه هوشمند
✅ حفظ تاریخچه گفتگو
✅ انتخاب مدل‌های مختلف

برای شروع، هر سوالی دارید بپرسید!
"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """پیام خوش‌آمدگویی"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in user_conversations:
        user_conversations[user_id] = {
            'messages': [],
            'model': 'llama3-70b',
            'max_tokens': 1000,
            'temperature': 0.7
        }
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔄 پاک کردن تاریخچه", callback_data='clear_history')
    btn2 = types.InlineKeyboardButton("📊 وضعیت", callback_data='status')
    btn3 = types.InlineKeyboardButton("🤖 انتخاب مدل", callback_data='select_model')
    btn4 = types.InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.reply_to(
        message, 
        f"سلام {user_name}! 👋\n\n{WELCOME_MESSAGE}", 
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_conversations:
        user_conversations[user_id]['messages'] = []
        bot.reply_to(message, "✅ تاریخچه مکالمه پاک شد!")
    else:
        bot.reply_to(message, "❌ هیچ تاریخچه‌ای وجود ندارد!")

@bot.message_handler(commands=['model'])
def show_models(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for model_id, model_name in AVAILABLE_MODELS.items():
        btn = types.InlineKeyboardButton(
            f"🤖 {model_name}", 
            callback_data=f'set_model_{model_id}'
        )
        markup.add(btn)
    
    bot.reply_to(
        message,
        "مدل مورد نظر خود را انتخاب کنید:",
        reply_markup=markup
    )

def call_ai_api(user_id, user_message):
    """ارسال درخواست به API هوش مصنوعی"""
    try:
        user_data = user_conversations.get(user_id, {
            'messages': [],
            'model': 'llama3-70b',
            'max_tokens': 1000,
            'temperature': 0.7
        })
        
        messages = []
        
        messages.append({
            "role": "system",
            "content": "شما Arvox هستید، یک دستیار هوش مصنوعی مفید و دوستانه. به زبان فارسی پاسخ دهید."
        })
        
        messages.extend(user_data['messages'])
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": user_data['model'],
            "messages": messages,
            "max_tokens": user_data['max_tokens'],
            "temperature": user_data['temperature'],
            "top_p": 0.9
        }
        
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            user_data['messages'].append({"role": "user", "content": user_message})
            user_data['messages'].append({"role": "assistant", "content": ai_response})
            
            if len(user_data['messages']) > 20:
                user_data['messages'] = user_data['messages'][-20:]
            
            user_conversations[user_id] = user_data
            
            return ai_response
        else:
            return f"❌ خطا در ارتباط با API: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "⏱️ زمان درخواست به پایان رسید. لطفاً دوباره تلاش کنید."
    except Exception as e:
        return f"❌ خطا: {str(e)}"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    bot.send_chat_action(message.chat.id, 'typing')
    
    response = call_ai_api(user_id, message.text)
    
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            bot.reply_to(message, response[i:i+4096])
    else:
        bot.reply_to(message, response)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == 'clear_history':
        if user_id in user_conversations:
            user_conversations[user_id]['messages'] = []
        bot.answer_callback_query(call.id, "✅ تاریخچه پاک شد!")
        bot.edit_message_text(
            "✅ تاریخچه مکالمه با موفقیت پاک شد!",
            call.message.chat.id,
            call.message.message_id
        )
    
    elif call.data == 'status':
        if user_id in user_conversations:
            user_data = user_conversations[user_id]
            model_name = AVAILABLE_MODELS.get(user_data['model'], user_data['model'])
            msg_count = len(user_data['messages']) // 2
            status_text = f"""
📊 **وضعیت فعلی:**

🤖 مدل فعال: {model_name}
💬 تعداد پیام‌ها: {msg_count}
🌡️ دما (Temperature): {user_data['temperature']}
📝 حداکثر توکن: {user_data['max_tokens']}
            """
            bot.answer_callback_query(call.id, "✅ وضعیت")
            bot.edit_message_text(
                status_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
    
    elif call.data == 'select_model':
        markup = types.InlineKeyboardMarkup(row_width=1)
        for model_id, model_name in AVAILABLE_MODELS.items():
            btn = types.InlineKeyboardButton(
                f"🤖 {model_name}", 
                callback_data=f'set_model_{model_id}'
            )
            markup.add(btn)
        
        bot.edit_message_text(
            "🤖 لطفاً مدل مورد نظر خود را انتخاب کنید:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif call.data == 'settings':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("🌡️ دما (Temperature)", callback_data='set_temp')
        btn2 = types.InlineKeyboardButton("📝 حداکثر توکن", callback_data='set_tokens')
        btn3 = types.InlineKeyboardButton("🔄 بازگشت", callback_data='back_to_main')
        markup.add(btn1, btn2, btn3)
        
        bot.edit_message_text(
            "⚙️ **تنظیمات:**\n\n"
            "• دما (Temperature): میزان خلاقیت پاسخ‌ها (0.1 تا 1.0)\n"
            "• حداکثر توکن: طول پاسخ (حداکثر 2000)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    elif call.data.startswith('set_model_'):
        model_id = call.data.replace('set_model_', '')
        if user_id in user_conversations:
            user_conversations[user_id]['model'] = model_id
            model_name = AVAILABLE_MODELS.get(model_id, model_id)
            bot.answer_callback_query(call.id, f"✅ مدل {model_name} فعال شد!")
            bot.edit_message_text(
                f"✅ مدل {model_name} با موفقیت فعال شد!",
                call.message.chat.id,
                call.message.message_id
            )
    
    elif call.data == 'back_to_main':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("🔄 پاک کردن تاریخچه", callback_data='clear_history')
        btn2 = types.InlineKeyboardButton("📊 وضعیت", callback_data='status')
        btn3 = types.InlineKeyboardButton("🤖 انتخاب مدل", callback_data='select_model')
        btn4 = types.InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')
        markup.add(btn1, btn2, btn3, btn4)
        
        bot.edit_message_text(
            WELCOME_MESSAGE,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📚 **راهنمای ربات Arvox**

**دستورات موجود:**
/start - شروع مجدد ربات
/clear - پاک کردن تاریخچه
/model - انتخاب مدل
/help - نمایش این راهنما

**ویژگی‌ها:**
• پاسخگویی هوشمند به سوالات
• حفظ تاریخچه مکالمه
• قابلیت انتخاب مدل‌های مختلف
• تنظیم دما و طول پاسخ

**مدل‌های موجود:**
• Llama 3 (پیشرفته) - بهترین کیفیت
• Llama 3 (سریع) - سرعت بالا
• Mixtral - متوسط
• Gemma - سبک
    """
    bot.reply_to(message, help_text, parse_mode="Markdown")

# اجرای ربات
if __name__ == "__main__":
    print("ربات Arvox با موفقیت شروع به کار کرد!")
    print(f"توکن تلگرام: {TOKEN[:10]}...")
    print("منتظر پیام‌های کاربران...")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\nربات متوقف شد.")
    except Exception as e:
        print(f"خطا: {e}")