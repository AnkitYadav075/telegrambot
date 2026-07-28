import requests
import json
from collections import defaultdict

# -----------------------------
# API URLs
# -----------------------------
TEACHERS_URL = "https://xukhvkiambbuoedvtznf.supabase.co/rest/v1/teachers?select=*&status=eq.verified&order=full_name.asc"

RATINGS_URL = "https://xukhvkiambbuoedvtznf.supabase.co/rest/v1/ratings?select=*"

# -----------------------------
# IMPORTANT:
# Open F12 -> Network -> teachers request
# Copy the "apikey" value from Request Headers
# Paste it below
# -----------------------------
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a2h2a2lhbWJidW9lZHZ0em5mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA1MjQxMTYsImV4cCI6MjA2NjEwMDExNn0.IWBMcUCeWCdYbT6p4q_H-KDJMekAUWYtY3MrSq6rpEs"
headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

print("Downloading teachers...")
teachers = requests.get(TEACHERS_URL, headers=headers).json()

print("Downloading ratings...")
ratings = requests.get(RATINGS_URL, headers=headers).json()

print(f"Teachers: {len(teachers)}")
print(f"Ratings : {len(ratings)}")

# -----------------------------
# Group ratings by teacher_id
# -----------------------------
grouped = defaultdict(list)

for r in ratings:
    grouped[r["teacher_id"]].append(r)

output = []

for teacher in teachers:

    teacher_id = teacher["id"]

    teacher_ratings = grouped.get(teacher_id, [])

    if teacher_ratings:

        teaching = sum(x["teaching"] for x in teacher_ratings) / len(teacher_ratings)
        evaluation = sum(x["evaluation"] for x in teacher_ratings) / len(teacher_ratings)
        behaviour = sum(x["behaviour"] for x in teacher_ratings) / len(teacher_ratings)
        internals = sum(x["internals"] for x in teacher_ratings) / len(teacher_ratings)

        overall = (
            teaching +
            evaluation +
            behaviour +
            internals
        ) / 4

        averages = [x["class_average"] for x in teacher_ratings]

        class_average = max(
            set(averages),
            key=averages.count
        )

    else:

        teaching = evaluation = behaviour = internals = overall = 0
        class_average = "N/A"

    output.append({
        "name": teacher["full_name"],
        "rating": round(overall, 2),
        "status": teacher["status"].upper(),
        "verified": True,
        "teaching": round(teaching, 2),
        "evaluation": round(evaluation, 2),
        "behaviour": round(behaviour, 2),
        "internals": round(internals, 2),
        "class_average": class_average
    })

with open("teachers.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4)

print("✅ teachers.json created successfully!")