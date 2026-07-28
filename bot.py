import os
import re
import json
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN not found in .env")
    raise SystemExit


# -----------------------------
# File path
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "teachers.json")


# -----------------------------
# Name normalisation
# Removes punctuation/case differences:
# "M. Suresh" -> "m suresh"
# "Monica P." -> "monica p"
# -----------------------------
def normalize_name(name):
    name = str(name).lower().strip()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


# Add confirmed spelling aliases here if needed.
# Only add aliases when you are sure they refer to the same teacher.
ALIASES = {
    # "abhishek shrivastav": "abhishek shrivastava",
    # "shweta mukherkjee": "shweta mukherjee",
    # "bhavana bhagerwal": "bhavana bagherwal",
    # "deep chandra uphadhya": "deep chandra upadhyay",
}


def canonical_name(name):
    normalized = normalize_name(name)
    return ALIASES.get(normalized, normalized)


# -----------------------------
# Numeric helpers
# -----------------------------
def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_valid_score(value):
    score = to_float(value)
    return score is not None and 0 <= score <= 5


def format_score(value):
    score = to_float(value)

    if score is None or score < 0 or score > 5:
        return "N/A"

    return f"{score:.2f}".rstrip("0").rstrip(".")


# -----------------------------
# Duplicate handling
# Keeps:
# 1. Record with valid non-zero rating
# 2. Verified record
# 3. More complete record
# -----------------------------
def record_rank(teacher):
    rating = to_float(teacher.get("rating", 0))

    has_valid_rating = int(rating is not None and 0 < rating <= 5)

    is_verified = int(
        teacher.get("verified") is True
        or str(teacher.get("status", "")).upper() == "VERIFIED"
    )

    valid_fields = sum(
        is_valid_score(teacher.get(field))
        for field in ["teaching", "evaluation", "behaviour", "internals"]
    )

    return has_valid_rating, is_verified, valid_fields


def remove_duplicates(records):
    unique_teachers = {}

    for teacher in records:
        name = teacher.get("name", "")
        key = canonical_name(name)

        if not key:
            continue

        if key not in unique_teachers:
            unique_teachers[key] = teacher
        else:
            existing = unique_teachers[key]

            # Replace only when the newer record is better.
            if record_rank(teacher) > record_rank(existing):
                unique_teachers[key] = teacher

    return list(unique_teachers.values())


# -----------------------------
# Load teachers.json
# -----------------------------
try:
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        raw_teachers = json.load(file)

    if not isinstance(raw_teachers, list):
        raise ValueError("teachers.json must contain a JSON array.")

    teachers = remove_duplicates(raw_teachers)

except Exception as e:
    print("❌ Error loading teachers.json")
    print(e)
    raise SystemExit


# -----------------------------
# Validate score data
# -----------------------------
for teacher in teachers:
    for field in ["rating", "teaching", "evaluation", "behaviour", "internals"]:
        value = teacher.get(field)

        if value is not None and not is_valid_score(value):
            print(
                f"⚠️ Invalid {field} for {teacher.get('name', 'Unknown')}: {value}"
            )

print(
    f"✅ Loaded {len(teachers)} unique teachers "
    f"from {len(raw_teachers)} total records"
)


# -----------------------------
# Extract search query
# Supports:
# /Lokesh
# /Lokesh Malviya
# /Lokesh@YourBotUsername Malviya
# -----------------------------
def get_query(text):
    text = text.strip()

    if text.startswith("/"):
        text = text[1:]

        # Removes @BotUsername only from first word.
        text = re.sub(r"^([^\s@]+)@[^\s]+", r"\1", text)

    return canonical_name(text)


# -----------------------------
# Start command
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Search a teacher using a command.\n\n"
        "Example:\n"
        "• /Aakash\n"
        "• /Lokesh"
    )


# -----------------------------
# Search teacher
# -----------------------------
async def search_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None or not update.message.text:
        return

    query = get_query(update.message.text)

    if len(query) < 2:
        await update.message.reply_text(
            "⚠️ Please enter at least 2 letters of a teacher's name."
        )
        return

    # First look for an exact normalized name match.
    exact_matches = [
        teacher
        for teacher in teachers
        if canonical_name(teacher.get("name", "")) == query
    ]

    # If no exact match, do partial matching.
    if exact_matches:
        matches = exact_matches
    else:
        matches = [
            teacher
            for teacher in teachers
            if query in canonical_name(teacher.get("name", ""))
        ]

    # -----------------------------
    # No teacher found
    # -----------------------------
    if not matches:
        await update.message.reply_text(
            "❌ No teacher found.\n\n"
            "Try entering a more accurate name."
        )
        return

    # -----------------------------
    # Multiple teachers found
    # -----------------------------
    if len(matches) > 1:
        max_results = 20
        shown_matches = matches[:max_results]

        msg = "🔍 Multiple teachers found:\n\n"

        for teacher in shown_matches:
            msg += f"• {teacher.get('name', 'Unknown')}\n"

        if len(matches) > max_results:
            msg += f"\n...and {len(matches) - max_results} more results."

        msg += "\n\nPlease type a more specific name."

        await update.message.reply_text(msg)
        return

    # -----------------------------
    # Single teacher found
    # -----------------------------
    teacher = matches[0]

    rating = to_float(teacher.get("rating"))

    if rating is None or rating <= 0 or rating > 5:
        recommendation = "⚠️ Rating data unavailable"
    elif rating >= 4.5:
        recommendation = "⭐⭐⭐⭐⭐ Highly Recommended"
    elif rating >= 3.5:
        recommendation = "⭐⭐⭐⭐ Recommended"
    elif rating >= 2.5:
        recommendation = "⭐⭐⭐ Average"
    else:
        recommendation = "⭐⭐ Not Recommended"

    status = teacher.get("status")

    if not status:
        if teacher.get("verified") is True:
            status = "Verified"
        else:
            status = "N/A"

    class_average = str(
        teacher.get("class_average", "N/A")
    ).title()

    final_remark = teacher.get("final_remark")

    message = (
        "👨‍🏫 Faculty Details\n\n"
        f"📛 Name: {teacher.get('name', 'N/A')}\n\n"
        f"⭐ Overall Rating: {format_score(teacher.get('rating'))}/5\n\n"
        f"📚 Teaching: {format_score(teacher.get('teaching'))}/5\n"
        f"📝 Evaluation: {format_score(teacher.get('evaluation'))}/5\n"
        f"😊 Behaviour: {format_score(teacher.get('behaviour'))}/5\n"
        f"📖 Internals: {format_score(teacher.get('internals'))}/5\n\n"
        f"📈 Class Average: {class_average}\n"
        f"🏷️ Status: {str(status).title()}\n\n"
        f"✅ {recommendation}"
    )

    if final_remark:
        message += f"\n\n💬 Remark: {final_remark}"

    await update.message.reply_text(message)


# -----------------------------
# Global error handler
# -----------------------------
async def error_handler(update, context):
    print(f"⚠️ Error: {context.error}")


# -----------------------------
# Start bot
# -----------------------------
app = Application.builder().token(TOKEN).build()

# /start command
app.add_handler(CommandHandler("start", start))

# Search using /teacher-name ONLY (normal messages ignored)
app.add_handler(
    MessageHandler(filters.COMMAND, search_teacher)
)

# Global error handler
app.add_error_handler(error_handler)

print("🤖 Bot Started Successfully!")

app.run_polling()
