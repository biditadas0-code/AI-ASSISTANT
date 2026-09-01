from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
from dotenv import load_dotenv
app = Flask(__name__)
load_dotenv()
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["chatbot_db"]
messages_collection = db["messages"]

# ---- GROQ API SETUP ----

GROQ_API_KEY =os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is not set. Please set your Groq API key."
    )

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ---- CHATBOT PERSONALITY ----

SYSTEM_PROMPT = (
    "You are a helpful personal assistant chatbot. "
    "You are named pixelmate.You are not ChatGPT, GPT-4, or any OpenAI product, and you must never claim to be one. If asked who made you or what model you are, say: 'I'm pixelmate , a custom chatbot built by Bidita using the Groq API."
    "You are great at solving real-life problems with practical, "
    "step-by-step advice."
    "You are also an expert programmer who can debug code in any language. "
    "When debugging, explain the bug clearly and show the corrected code."
)

# ---- CONVERSATION MEMORY ----
# This memory resets whenever the Flask server restarts.

conversation_history = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


# ---- HOME PAGE ----

@app.route("/")
def home():
    return render_template("index.html")


# ---- CHAT API ----

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({
            "reply": "Please type something!"
        })

    # Add user's message
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    conversation_history[:] = conversation_history[-6:]

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=conversation_history,
            temperature=0.7,
            max_tokens=2048
        )

        reply = response.choices[0].message.content

        # Save conversation to MongoDB
        messages_collection.insert_one({
            "user_message": user_message,
            "bot_reply": reply
    })

        # Save AI response
        conversation_history.append({
            "role": "assistant",
            "content": reply
        })

        return jsonify({
            "reply": reply
        })

    except Exception as e:

        # Remove user's message if API failed
        conversation_history.pop()

        print("Groq API Error:", str(e))

        return jsonify({
            "reply": "Sorry, I couldn't connect to the AI right now."
        }), 500


# ---- START FLASK ----

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000
    )

