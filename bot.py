import os
import json
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# Load BOT TOKEN
# -----------------------------
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN not found in .env")
    exit()

# -----------------------------
# Load teachers.json
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "teachers.json")

try:
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        teachers = json.load(file)
except Exception as e:
    print("❌ Error loading teachers.json")
    print(e)
    exit()

print(f"✅ Loaded {len(teachers)} teachers")


# -----------------------------
# Search Teacher
# -----------------------------
async def search_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None:
        return

    query = update.message.text.strip().lower()

    if query.startswith("/"):
        query = query[1:]

# Remove @BotUsername if present (e.g. /lokesh@YourBot)
    query = query.split("@")[0]

    # query = update.message.text.strip().lower()

    # # allow /lokesh
    # if query.startswith("/"):
    #     query = query[1:]

    matches = []

    for teacher in teachers:
        name = teacher.get("name", "").lower()

        if query in name:
            matches.append(teacher)

    # -----------------------------
    # No teacher found
    # -----------------------------
    if len(matches) == 0:
        await update.message.reply_text(
            "❌ No teacher found."
        )
        return

    # -----------------------------
    # Multiple teachers found
    # -----------------------------
    if len(matches) > 1:

        msg = "🔍 Multiple teachers found:\n\n"

        for t in matches:
            msg += f"• {t['name']}\n"

        msg += "\nPlease type a more specific name."

        await update.message.reply_text(msg)
        return

    # -----------------------------
    # Single teacher
    # -----------------------------
    teacher = matches[0]

    rating = float(teacher.get("rating", 0))

    if rating >= 4.5:
        recommendation = "⭐⭐⭐⭐⭐ Highly Recommended"
    elif rating >= 3.5:
        recommendation = "⭐⭐⭐⭐ Recommended"
    elif rating >= 2.5:
        recommendation = "⭐⭐⭐ Average"
    else:
        recommendation = "⭐⭐ Not Recommended"

    message = f"""
👨‍🏫 Faculty Details

📛 Name: {teacher.get('name', 'N/A')}

⭐ Overall Rating: {teacher.get('rating', 0)}/5

📚 Teaching: {teacher.get('teaching', 0)}/5
📝 Evaluation: {teacher.get('evaluation', 0)}/5
😊 Behaviour: {teacher.get('behaviour', 0)}/5
📖 Internals: {teacher.get('internals', 0)}/5

📈 Class Average: {str(teacher.get('class_average', 'N/A')).title()}

🏷️ Status: {str(teacher.get('status', 'Unknown')).title()}

✅ {recommendation}
"""

    await update.message.reply_text(message)


# -----------------------------
# Start Bot
# -----------------------------
app = Application.builder().token(TOKEN).build()

# Handle every command like /lokesh
app.add_handler(
    MessageHandler(filters.COMMAND, search_teacher)
)

print("🤖 Bot Started Successfully!")

app.run_polling()