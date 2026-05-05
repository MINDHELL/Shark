import asyncio
import requests
import json
import os
from pyrogram import filters
from bot import Bot as app
from config import ADMIN_ID, NEWS_API_KEY

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

# ===== GET NEWS =====
def get_news():
    q = data["category"] if data["category"] != "general" else "india"

    url = f"https://newsapi.org/v2/everything?q={q}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    res = requests.get(url).json()

    if res.get("status") != "ok":
        print("API Error:", res)
        return []

    news = []
    for a in res.get("articles", []):
        title = a.get("title")
        link = a.get("url")
        image = a.get("urlToImage")

        if title:
            news.append((title, link, image))

    return news

# ===== SEND TO CHANNELS =====
async def send_to_channels(title, link, image):
    for ch in data["channels"]:
        try:
            caption = f"📰 {title}\n\n👉 Read more:\n{link}"

            if image:
                await app.send_photo(
                    chat_id=ch,
                    photo=image,
                    caption=caption
                )
            else:
                await app.send_message(
                    chat_id=ch,
                    text=caption,
                    disable_web_page_preview=True
                )

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Error sending to {ch}:", e)

# ===== AUTO LOOP =====
async def auto_news():
    global running
    print("AUTO LOOP STARTED")

    while True:
        if running and data["channels"]:
            try:
                news = get_news()

                for title, link, image in news:
                    if title in sent_news:
                        continue

                    sent_news.add(title)

                    # prevent memory overflow
                    if len(sent_news) > 200:
                        sent_news.clear()

                    await send_to_channels(title, link, image)

                print("News sent")

            except Exception as e:
                import traceback
                print("Error:", e)
                traceback.print_exc()

        await asyncio.sleep(data["interval"])

# ===== COMMANDS =====

@app.on_message(filters.command("startnews") & filters.user(ADMIN_ID))
async def start(_, msg):
    global running
    running = True
    await msg.reply("✅ News started")

@app.on_message(filters.command("stopnews") & filters.user(ADMIN_ID))
async def stop(_, msg):
    global running
    running = False
    await msg.reply("⛔ News stopped")

@app.on_message(filters.command("latestnews"))
async def latest(_, msg):
    news = get_news()

    if not news:
        return await msg.reply("No news ❌")

    for title, link, image in news[:3]:
        caption = f"📰 {title}\n\n👉 Read more:\n{link}"

        if image:
            await msg.reply_photo(photo=image, caption=caption)
        else:
            await msg.reply(caption, disable_web_page_preview=True)

# ===== CHANNEL MANAGEMENT =====

@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_channel(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /addchannel @channel")

    ch = msg.command[1]

    if ch in data["channels"]:
        return await msg.reply("Already added")

    if not ch.startswith("@") and not ch.startswith("-100"):
        return await msg.reply("Invalid channel format")

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
    if len(msg.command) < 2:
        return await msg.reply("Usage: /settime 120")

    try:
        t = int(msg.command[1])
        if t < 30:
            return await msg.reply("Min 30 sec")

        data["interval"] = t
        save_data()
        await msg.reply(f"⏱ Set to {t} sec")

    except:
        await msg.reply("Invalid number")

@app.on_message(filters.command("setcategory") & filters.user(ADMIN_ID))
async def set_category(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /setcategory keyword")

    data["category"] = msg.command[1]
    save_data()
    await msg.reply(f"📂 {data['category']}")

@app.on_message(filters.command("status"))
async def status(_, msg):
    await msg.reply(
        f"📊 STATUS\n\nChannels: {len(data['channels'])}\nInterval: {data['interval']} sec\nCategory: {data['category']}\nRunning: {running}"
    )

# ===== TEST =====

@app.on_message(filters.command("testnews"))
async def test_news(_, msg):
    news = get_news()

    if not news:
        return await msg.reply("No news fetched ❌")

    for title, link, image in news[:3]:
        caption = f"📰 {title}\n\n👉 Read more:\n{link}"

        if image:
            await msg.reply_photo(photo=image, caption=caption)
        else:
            await msg.reply(caption, disable_web_page_preview=True)

# ===== AUTO START LOOP =====

async def init_news():
    await asyncio.sleep(5)
    print("Starting auto news loop...")
    asyncio.create_task(auto_news())

asyncio.get_event_loop().create_task(init_news())
