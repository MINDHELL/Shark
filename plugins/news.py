import requests
import time
import threading
import json
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ===== CONFIG =====
BOT_TOKEN = "8460769837:AAFVv6GDtzSuKxJLAKiqvCq1Ldx66KO21Es"
NEWS_API_KEY = "07b674b8dafc4539910ce689e9d64059"
ADMIN_ID = 8635942785  # <-- YOUR TELEGRAM USER ID

DATA_FILE = "data.json"

# ===== LOAD / SAVE =====

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "channels": [],
            "interval": 300,
            "category": "general"
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data = load_data()
sent_news = set()
running = True

# ===== HELPERS =====

def is_admin(update):
    return update.effective_user.id == ADMIN_ID


def get_news():
    url = f"https://newsapi.org/v2/top-headlines?country=in&category={data['category']}&apiKey={NEWS_API_KEY}"
    res = requests.get(url).json()

    news = []
    for a in res.get("articles", []):
        title = a["title"]
        link = a["url"]

        if title not in sent_news:
            news.append((title, link))
            sent_news.add(title)

    return news


def send_to_channels(bot, msg):
    for ch in data["channels"]:
        try:
            bot.send_message(chat_id=ch, text=msg)
            time.sleep(1)
        except Exception as e:
            print(f"Error {ch}: {e}")


# ===== AUTO LOOP =====

def auto_news(bot):
    global running
    while True:
        if running and data["channels"]:
            try:
                news = get_news()

                for title, link in news[:5]:
                    msg = f"📰 {title}\n\n🔗 {link}"
                    send_to_channels(bot, msg)

                print("News sent.")
            except Exception as e:
                print("Error:", e)

        time.sleep(data["interval"])


# ===== COMMANDS =====

def start(update: Update, context: CallbackContext):
    if not is_admin(update): return
    global running
    running = True
    update.message.reply_text("✅ Bot started")


def stop(update: Update, context: CallbackContext):
    if not is_admin(update): return
    global running
    running = False
    update.message.reply_text("⛔ Bot stopped")


def latest(update: Update, context: CallbackContext):
    news = get_news()
    for t, l in news[:5]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{t}\n{l}")


# ===== CHANNEL MANAGEMENT =====

def add_channel(update: Update, context: CallbackContext):
    if not is_admin(update): return

    if not context.args:
        update.message.reply_text("Usage: /addchannel @channel")
        return

    ch = context.args[0]

    if ch in data["channels"]:
        update.message.reply_text("Already added")
        return

    data["channels"].append(ch)
    save_data()

    update.message.reply_text(f"✅ Added {ch}")


def remove_channel(update: Update, context: CallbackContext):
    if not is_admin(update): return

    if not context.args:
        update.message.reply_text("Usage: /removechannel @channel")
        return

    ch = context.args[0]

    if ch not in data["channels"]:
        update.message.reply_text("Not found")
        return

    data["channels"].remove(ch)
    save_data()

    update.message.reply_text(f"❌ Removed {ch}")


def list_channels(update: Update, context: CallbackContext):
    if not data["channels"]:
        update.message.reply_text("No channels set")
        return

    update.message.reply_text("\n".join(data["channels"]))


# ===== SETTINGS =====

def set_time(update: Update, context: CallbackContext):
    if not is_admin(update): return

    try:
        t = int(context.args[0])
        if t < 30:
            update.message.reply_text("Min 30 sec")
            return

        data["interval"] = t
        save_data()

        update.message.reply_text(f"⏱ Set to {t} sec")
    except:
        update.message.reply_text("Usage: /settime 120")


def set_category(update: Update, context: CallbackContext):
    if not is_admin(update): return

    if not context.args:
        update.message.reply_text("Usage: /setcategory tech/business/sports")
        return

    data["category"] = context.args[0]
    save_data()

    update.message.reply_text(f"📂 {data['category']}")


def status(update: Update, context: CallbackContext):
    msg = f"""
📊 STATUS

Channels: {len(data['channels'])}
Interval: {data['interval']} sec
Category: {data['category']}
Running: {running}
"""
    update.message.reply_text(msg)


# ===== MAIN =====

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("latest", latest))

    dp.add_handler(CommandHandler("addchannel", add_channel))
    dp.add_handler(CommandHandler("removechannel", remove_channel))
    dp.add_handler(CommandHandler("channels", list_channels))

    dp.add_handler(CommandHandler("settime", set_time))
    dp.add_handler(CommandHandler("setcategory", set_category))
    dp.add_handler(CommandHandler("status", status))

    updater.start_polling()

    threading.Thread(target=auto_news, args=(updater.bot,), daemon=True).start()

    updater.idle()


if __name__ == "__main__":
    main()

  
