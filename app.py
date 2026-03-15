import sqlite3
import os
import sys
import urllib.parse
import math
import random 
import webbrowser
from threading import Timer
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI

# --------------------------
# 🔑 API KEY
# --------------------------
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

# --- SETUP PENTRU EXECUTABIL (PATH FIX) ---
# Asta este singura modificare majoră: ne asigurăm că Python găsește fișierele
# chiar și când sunt "împachetate" în interiorul .exe-ului.
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)

DB_NAME = "safety_resources.db"
SCRAPED_FILE = os.path.join(BASE_DIR, "scraped_knowledge.txt")

# --- MEMORY FOR COOKING CHAT ---
cooking_history = [
    {"role": "system", "content": "You are a friendly chef. Answer shortly in English."}
]

# --- RUTE PENTRU INTERFAȚĂ ---
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, 'index_final.html')

@app.route("/documentatie.html")
def docs():
    return send_from_directory(BASE_DIR, 'documentatie.html')

# --------------------------
# 1. DATABASE SETUP
# --------------------------
def init_db():
    db_path = os.path.join(BASE_DIR, DB_NAME)
    
    # Pentru exe, recreăm baza de date la fiecare rulare (safe pentru demo)
    if os.path.exists(db_path) and not getattr(sys, 'frozen', False):
        try: os.remove(db_path)
        except: pass 
        
    # Dacă suntem în exe, folosim baza de date din temp sau o creăm în memorie dacă e nevoie
    # Aici o lăsăm să se creeze unde rulează scriptul
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY, category TEXT, name TEXT, address TEXT, phone TEXT, website TEXT, description TEXT, lat REAL, lon REAL)''')
    
    real_data = [
        ("police", "Bucharest Police (General Directorate)", "Calea Victoriei 19", "021 315 35 34", "https://b.politiaromana.ro", "General Police Directorate.", 44.4355, 26.0959),
        ("lawyer", "Bucharest Bar Association", "Str. Dr. Râureanu nr. 3", "021 311 22 93", "https://www.baroul-bucuresti.ro", "Free Legal Aid.", 44.4334, 26.0942),
        ("ngo", "ANAIS Association", "Str. Agricultori nr. 116A", "0799 493 853", "https://anais.org.ro", "Emergency shelter.", 44.4390, 26.1285),
        ("ngo", "FILIA Center", "Bd. Pache Protopopescu nr. 9", "021 311 12 13", "https://centrulfilia.ro", "Advocacy & Support.", 44.4410, 26.1150),
        ("self-defense", "Krav Maga Dacians", "Splaiul Independenței 319", "0744 333 222", "https://kravmagadacians.ro", "Self-defense classes.", 44.4445, 26.0450),
        ("ngo", "Domestic Violence Helpline (ANES)", "National (Toll-Free)", "0800 500 333", "https://anes.gov.ro", "National toll-free number.", 0.0, 0.0),
        ("police", "EMERGENCY SERVICE 112", "Anywhere", "112", "https://www.sts.ro", "FOR MAJOR EMERGENCIES ONLY.", 0.0, 0.0)
    ]
    cursor.executemany('INSERT INTO resources (category, name, address, phone, website, description, lat, lon) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', real_data)
    conn.commit()
    conn.close()

init_db()

# --------------------------
# 2. UTILS
# --------------------------
SAFETY_KEYWORDS = [
    "help", "violence","weapon","knife","dangerous", "abuse", "danger", "police", "lawyer", "ngo", "hit", "beat", "defense", 
    "mail", "email", "complaint", "fear", "hide", "plan", "list", "scared", "victim", 
    "whatsapp", "text", "message", "talk", "sms", "alone", "urgent", "emergency", "hurt",
    "shopping", "escape", "recipe"
]

def detect_safety(message):
    return any(kw in message.lower() for kw in SAFETY_KEYWORDS)

def get_scraped_context():
    try:
        if os.path.exists(SCRAPED_FILE):
            with open(SCRAPED_FILE, "r", encoding="utf-8") as f: return f.read()
    except: pass
    return ""

def calculate_distance(lat1, lon1, lat2, lon2):
    if lat2 == 0.0 or lon2 == 0.0: return 9999
    try:
        R = 6371 
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except: return 9999

# --------------------------
# 3. GENERATORS
# --------------------------

def query_database_html(user_text, user_lat=None, user_lon=None):
    user_text = user_text.lower()
    category = "ngo"
    if "lawyer" in user_text: category = "lawyer"
    elif "police" in user_text or "112" in user_text: category = "police"
    elif "class" in user_text or "defense" in user_text: category = "self-defense"
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    if "help" in user_text:
        cursor.execute("SELECT * FROM resources WHERE category IN ('ngo', 'police')")
    else:
        cursor.execute("SELECT * FROM resources WHERE category = ?", (category,))
    
    rows = cursor.fetchall()
    conn.close()
    if not rows: return ""

    results = []
    for row in rows:
        dist_str = ""
        sort_key = 9999
        if user_lat and user_lon and row['lat'] != 0.0:
            dist = calculate_distance(float(user_lat), float(user_lon), row['lat'], row['lon'])
            dist_str = f" • <b>{dist:.1f} km away</b>"
            sort_key = dist
        results.append({
            "html": f'''<div class="resource-card"><div class="res-title">{row['name']}</div><div class="res-row"><span>Type:</span> {row['category'].upper()}</div><div class="res-row"><span>Location:</span> {row['address']} {dist_str}</div><div class="res-row"><span>Phone:</span> <a href="tel:{row['phone'].replace(' ', '')}">{row['phone']}</a></div><div class="res-desc">{row['description']}</div></div>''',
            "sort": sort_key
        })
    results.sort(key=lambda x: x['sort'])
    html_out = f'<h3 style="margin-top:20px; border-top:1px solid #eee; padding-top:15px;">Nearest Verified Resources:</h3>'
    for item in results: html_out += item['html']
    return html_out

def analyze_urgency_score(user_message):
    system_prompt = "You are an AI Risk Assessment module. Rate risk 1-10. If user says help/hit/scared -> MINIMUM 7. Return NUMBER only."
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}])
        score = int(response.choices[0].message.content.strip())
    except: score = 5 
    if detect_safety(user_message) and score < 5: score = 5
    return score

def generate_web_advice(user_message):
    scraped = get_scraped_context()
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": f"Give 1 paragraph safety advice IN ENGLISH using: {scraped[:4000]}"}, {"role": "user", "content": user_message}])
        return response.choices[0].message.content
    except: return "Stay safe."

# === AGENTIC ACTIONS ===

def generate_mailto_link(user_message, lat=None, lon=None):
    loc_str = "[INSERT ADDRESS]"
    if lat and lon: 
        loc_str = f"https://www.google.com/maps?q={lat},{lon}"
    system_prompt = f"""
    Write a VERY SHORT, FORMAL email body to the Police IN ENGLISH.
    Do NOT invent details. Use clear placeholders: [MY NAME].
    The location is already detected as: {loc_str} -> INCLUDE THIS EXACTLY.
    Example body: "I request urgent assistance. I am at {loc_str}. My name is [MY NAME]. Please help."
    Do not add subject line here.
    """
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}])
        body = response.choices[0].message.content
    except: body = f"URGENT HELP NEEDED at {loc_str}"
    return f"mailto:politia@b.politiaromana.ro?subject=SOS-URGENT&body={urllib.parse.quote(body)}"

def generate_whatsapp_link(user_message, lat=None, lon=None):
    loc_str = "[My Address]"
    if lat and lon: 
        loc_str = f"https://www.google.com/maps?q={lat},{lon}"
    system_prompt = f"Write short WhatsApp SOS IN ENGLISH. Include location: {loc_str}. Return ONLY message."
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}])
        body = response.choices[0].message.content
    except: body = f"Help me. {loc_str}"
    return f"https://wa.me/?text={urllib.parse.quote(body)}"

def generate_fake_plan(user_message):
    detailed_safety_plan = """
    =========================================
    SECRET INGREDIENTS (DETAILED SAFETY PLAN)
    =========================================
    
    1. URGENT EXIT STRATEGY
    - Identify the safest room in the house (preferably with a window/exit, avoid kitchens/bathrooms where objects can be weapons).
    - Practice escape routes with your children (treat it as a "fire drill" game).
    - Keep a "Go-Bag" hidden near the exit or at a trusted neighbor's house.
    - If arguments escalate, back towards the exit, never into a corner.

    2. THE "GO-BAG" ESSENTIALS (Prepare in advance)
    - DOCUMENTS: ID/Passport, Birth certificates, Medical records, Lease/Deed, Protection orders (Originals or Photos on phone).
    - MONEY: Cash is vital (credit cards are traceable). Spare keys (car/house).
    - MEDICATION: Essential prescriptions for you and children for at least 1 week.
    - COMMUNICATION: A burner phone or a prepaid SIM card.
    - CLOTHING: A change of clothes for everyone.

    3. DIGITAL SECURITY (CRITICAL)
    - Change passwords for Email, Banking, and Social Media immediately. Use strong, unique passwords.
    - Turn off "Location Services" on your phone for all apps except Maps when needed.
    - Use "Incognito Mode" for browsing.
    - Check your phone for unknown apps (stalkerware) and remove them.

    4. COMMUNICATION CODE
    - Establish a code word with neighbors/family (e.g., "I made lasagna") which means "Call 911 immediately".
    - Do not tell the abuser you are leaving until you are already safe.

    5. CONTACTS
    - Police: 112 (Europe/General Emergency)
    - Domestic Violence Helpline: 0800 500 333 (Romania)
    - Trust your instincts. If you feel unsafe, leave immediately.
    """
    
    recipes = ["Chocolate_Cake", "Beef_Stew", "Apple_Pie", "Pasta_Carbonara"]
    selected_dish = random.choice(recipes)
    filename = f"{selected_dish}_Recipe_List.txt"
    system_prompt = f"Generate {selected_dish} RECIPE in ENGLISH. Ingredients & Steps only."
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": "Generate"}])
        content = response.choices[0].message.content + ("\n"*150) + detailed_safety_plan
        return content, filename
    except: return "Error", "Error.txt"

# --------------------------
# 4. ENDPOINT
# --------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    user_lat = data.get("lat")
    user_lon = data.get("lon")
    text_lower = user_message.lower()
    
    is_safety = detect_safety(user_message)
    mode = "safety" if is_safety else "cooking"
    answer, action, action_payload, action_filename = "", None, None, None

    if mode == "cooking":
        cooking_history.append({"role": "user", "content": user_message})
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=cooking_history)
            answer = response.choices[0].message.content
            cooking_history.append({"role": "assistant", "content": answer})
        except: answer = "I can help with recipes."
    else:
        # SAFETY
        urgency = analyze_urgency_score(user_message)
        urgency_html = f'<div class="urgency-badge">⚠️ AI Risk Level: {urgency}/10</div>'
        web_advice = generate_web_advice(user_message)
        advice_html = f'<div class="web-advice-box"><b>🛡️ Expert Protocol (Source: NCBI):</b><br>{web_advice}</div>'
        cards_html = query_database_html(user_message, user_lat, user_lon)
        
        hints_html = """
        <div style="margin-top:20px; padding:10px; background:#fff3e0; border-radius:5px; font-size:13px; color:#e65100;">
            <b>💡 Need to take action? Try typing:</b><br>
            • "help" -> Drafts a police report.<br>
            • "sms" -> Alerts family.<br>
            • "Shopping list" -> Downloads the hidden plan.<br>
            • "Clean Safety" -> Immediate exit.
        </div>
        """
        
        answer = f"{urgency_html}<br>{advice_html}<br>{cards_html}<br>{hints_html}"

        if any(k in text_lower for k in ["hide", "panic"]): action = "panic_mode"
        elif any(k in text_lower for k in ["plan", "list", "shopping"]): 
            action = "download_plan"
            action_payload, action_filename = generate_fake_plan(user_message)
            answer = f"<b>Safety Plan Generated.</b><br>{answer}"
        elif any(k in text_lower for k in ["whatsapp", "sms"]): 
            action = "open_whatsapp"
            action_payload = generate_whatsapp_link(user_message, user_lat, user_lon)
            answer = f"<b>WhatsApp Ready.</b><br>{answer}"
        elif any(k in text_lower for k in ["help", "email"]): 
            action = "open_email"
            action_payload = generate_mailto_link(user_message, user_lat, user_lon)
            answer = f"<b>Email Ready.</b><br>{answer}"

    return jsonify({"mode": mode, "answer": answer, "action": action, "action_payload": action_payload, "action_filename": action_filename})

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(port=5000)