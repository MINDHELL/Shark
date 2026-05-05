import asyncio
import requests
import json
import os
from pyrogram import Client, filters
from config import OWNER_ID, ADMIN_ID, APP_ID, API_HASH, TG_BOT_TOKEN


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

# ===== APP =====
app = Client("news_bot", api_id=APP_ID, api_hash=API_HASH, bot_token=TG_BOT_TOKEN)

# ===== HELPERS =====
def is_admin(user_id):
    return user_id == ADMIN_ID

def get_news():
    url = f"https://newsapi.org/v2/top-headlines?country=in&category={data['category']}&apiKey=07b674b8dafc4539910ce689e9d64059"
    res = requests.get(url).json()

    news = []
    for a in res.get("articles", []):
        title = a["title"]
        link = a["url"]

        if title not in sent_news:
            news.append((title, link))
            sent_news.add(title)

    return news

async def send_to_channels(msg):
    for ch in data["channels"]:
        try:
            await app.send_message(ch, msg)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error {ch}: {e}")

# ===== AUTO LOOP =====
async def auto_news():
    global running
    while True:
        if running and data["channels"]:
            try:
                news = get_news()

                for title, link in news[:5]:
                    msg = f"📰 {title}\n\n🔗 {link}"
                    await send_to_channels(msg)

                print("News sent")
            except Exception as e:
                print("Error:", e)

        await asyncio.sleep(data["interval"])

# ===== COMMANDS =====

@app.on_message(filters.command("startnews") & filters.user(ADMIN_ID))
async def start(_, msg):
    global running
    running = True
    await msg.reply("✅ Bot started")

@app.on_message(filters.command("stopnews") & filters.user(ADMIN_ID))
async def stop(_, msg):
    global running
    running = False
    await msg.reply("⛔ Bot stopped")

@app.on_message(filters.command("latestnews"))
async def latest(_, msg):
    news = get_news()
    for t, l in news[:5]:
        await msg.reply(f"{t}\n{l}")

# ===== CHANNEL MANAGEMENT =====

@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_channel(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /addchannel @channel")

    ch = msg.command[1]

    if ch in data["channels"]:
        return await msg.reply("Already added")

    data["channels"].append(ch)
    save_data()
    await msg.reply(f"✅ Added {ch}")

@app.on_message(filters.command("removechannel") & filters.user(ADMIN_ID))
async def remove_channel(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /removechannel @channel")

    ch = msg.command[1]

    if ch not in data["channels"]:
        return await msg.reply("Not found")

    data["channels"].remove(ch)
    save_data()
    await msg.reply(f"❌ Removed {ch}")

@app.on_message(filters.command("channels"))
async def list_channels(_, msg):
    if not data["channels"]:
        return await msg.reply("No channels set")

    await msg.reply("\n".join(data["channels"]))

# ===== SETTINGS =====

@app.on_message(filters.command("settime") & filters.user(ADMIN_ID))
async def set_time(_, msg):
    try:
        t = int(msg.command[1])
        if t < 30:
            return await msg.reply("Min 30 sec")

        data["interval"] = t
        save_data()
        await msg.reply(f"⏱ Set to {t} sec")
    except:
        await msg.reply("Usage: /settime 120")

@app.on_message(filters.command("setcategory") & filters.user(ADMIN_ID))
async def set_category(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /setcategory tech/business")

    data["category"] = msg.command[1]
    save_data()
    await msg.reply(f"📂 {data['category']}")

@app.on_message(filters.command("status"))
async def status(_, msg):
    await msg.reply(
        f"📊 STATUS\n\nChannels: {len(data['channels'])}\nInterval: {data['interval']} sec\nCategory: {data['category']}\nRunning: {running}"
    )

# ===== RUN ====

async def main():
    await app.start()
    print("Bot running...")
    asyncio.create_task(auto_news())
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()

