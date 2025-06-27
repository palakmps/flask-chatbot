import os
import secrets
import fitz  # PyMuPDF for reading PDFs
from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import re
import requests
from transformers import pipeline, AutoModelForQuestionAnswering, AutoTokenizer
from rapidfuzz import process  # Fuzzy matching for better FAQ handling

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

MODEL_NAME = "deepset/roberta-base-squad2"
qa_pipeline = None

def load_qa_pipeline():
    model = AutoModelForQuestionAnswering.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return pipeline("question-answering", model=model, tokenizer=tokenizer)

@app.before_request
def ensure_model_loaded():
    global qa_pipeline
    if qa_pipeline is None:
        qa_pipeline = load_qa_pipeline()

tf = TimezoneFinder()
geolocator = Nominatim(user_agent="chatbot")

CURRENCY_API_KEY = "d011d9834c6d00735306f207"
CURRENCY_API_URL = f"https://v6.exchangerate-api.com/v6/{CURRENCY_API_KEY}/latest/"

faqs = {
    "hi": "Hello! How can I help you?",
    "how are you": "Thank You but I'm still learning😊",
    "what is your name": "Thank You but I'm still learning😊.",
    "what can you do": "I can answer your frequently asked questions.",
    "how can i contact support": "You can contact support via email at support@example.com.",
    "what is the basic format and structure of a manuscript": "A manuscript generally includes a Title Page, Abstract, Keywords, and the Main Text, which is divided into sections like Introduction, Methods, Results, Discussion, and Conclusion.",
    "what details should be included on the title page of a manuscript": "The title page should have a clear and descriptive title, author names, affiliations, and contact information for the corresponding author.",
    "how long should the abstract be and what should it cover": "The abstract is typically between 150-300 words and should summarize the study's purpose, methods, results, and conclusions.",
    "what purpose do keywords serve in a manuscript": "Keywords, usually 3-10 words or phrases, help to categorize the manuscript by topic and aid in its discoverability.",
    "what is the typical structure of the main text in a manuscript": "The main text is structured into sections: Introduction, Methods, Results, Discussion, and Conclusion.",
    "what information is typically covered in the introduction section": "The Introduction provides background information and the purpose of the study.",
    "why is the methods section important in a manuscript": "The Methods section gives a detailed description of the research methods, allowing others to replicate the study.",
    "what should the results section of a manuscript include": "The Results section presents the findings of the study, often accompanied by tables or figures.",
    "what is discussed in the discussion section of a manuscript": "The Discussion section interprets the results, addresses limitations, and explores the implications of the findings.",
    "what is the purpose of the conclusion section in a manuscript": "The Conclusion summarizes the study and may suggest directions for future research.",
    "what fonts are generally recommended for manuscript formatting": "Manuscripts are typically formatted in standard fonts like Times New Roman or Arial, in size 11 or 12.",
    "what is the recommended line spacing and margin size for manuscripts": "Manuscripts should be double-spaced with margins of at least 1 inch on all sides.",
    "where should page numbers be placed in a manuscript": "Page numbers should appear on all pages, typically in the top or bottom right corner."
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/read')
def read_file():
    filename = session.get("uploaded_file")
    if not filename:
        return "No file uploaded"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        text = ""
        if filename.endswith('.pdf'):
            pdf = fitz.open(filepath)
            for page in pdf:
                text += page.get_text()
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
    return render_template("read.html", text=text)

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

def get_live_exchange_rate(from_currency, to_currency):
    try:
        response = requests.get(CURRENCY_API_URL + from_currency)
        data = response.json()
        if response.status_code == 200 and "conversion_rates" in data:
            return data["conversion_rates"].get(to_currency)
    except Exception as e:
        print(f"Exchange rate error: {e}")
    return None

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.json.get("question", "").strip()
    lower_input = user_input.lower()

    # 1. Handle general time queries without location
    if re.fullmatch(r"(what time is it|what's the time|time now|current time)", lower_input):
        return jsonify({"response": "Could you please specify the city or country you want the time for?"})

    # 2. Handle time queries with city
    time_city_match = re.search(r"(?:time in|what time is it in|current time in)\s+([\w\s]+)", lower_input)
    if time_city_match:
        city = time_city_match.group(1).strip()
        try:
            location = geolocator.geocode(city, timeout=5)
            if location:
                timezone = tf.timezone_at(lng=location.longitude, lat=location.latitude)
                if timezone:
                    local_time = datetime.now(pytz.timezone(timezone)).strftime('%Y-%m-%d %H:%M:%S')
                    return jsonify({"response": f"The current time in {city.title()} is {local_time}."})
            return jsonify({"response": "Sorry, I couldn't determine the time for that location."})
        except Exception as e:
            print(f"Time lookup error: {e}")
            return jsonify({"response": "Sorry, I couldn't determine the time for that location."})

    # 3. Handle currency conversion
    currency_match = re.search(
        r'(\d+(?:\.\d+)?)\s*([A-Za-z₹$€£]+)\s*(?:to|in|into)\s*([A-Za-z₹$€£]+)', lower_input
    )
    if currency_match:
        amount = float(currency_match.group(1))
        from_currency_raw = currency_match.group(2).upper()
        to_currency_raw = currency_match.group(3).upper()

        symbol_map = {"$": "USD", "₹": "INR", "€": "EUR", "£": "GBP"}
        from_currency = symbol_map.get(from_currency_raw, from_currency_raw)
        to_currency = symbol_map.get(to_currency_raw, to_currency_raw)

        exchange_rate = get_live_exchange_rate(from_currency, to_currency)
        if exchange_rate:
            converted_amount = round(amount * exchange_rate, 2)
            return jsonify({"response": f"{amount} {from_currency} is equal to {converted_amount} {to_currency} (Live Rate)."})
        return jsonify({"response": f"Sorry, I couldn't fetch the exchange rate for {from_currency} to {to_currency}."})

    # 4. FAQ fuzzy match
    faq_dict = {q.lower(): a for q, a in faqs.items()}
    best_match, score, _ = process.extractOne(lower_input, faq_dict.keys(), score_cutoff=70)
    if best_match:
        return jsonify({"response": faq_dict[best_match]})

    # 5. Default fallback
    return jsonify({"response": "Thanks, but I'm still learning 😊"})


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file uploaded"
    file = request.files['file']
    if file.filename == '':
        return "No file selected"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)
    session["uploaded_file"] = file.filename
    return redirect(url_for("read_file"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
