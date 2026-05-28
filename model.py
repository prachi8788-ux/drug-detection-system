import pickle
import streamlit as st
import pandas as pd
import asyncio
import nest_asyncio
from telethon import TelegramClient
from streamlit_option_menu import option_menu
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# Load ML model + metrics
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
metrics = pickle.load(open("metrics.pkl", "rb"))

nest_asyncio.apply()

st.set_page_config(page_title="AI Message Monitor", layout="wide")

# Session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "flagged_messages" not in st.session_state:
    st.session_state.flagged_messages = []
if "telegram_messages" not in st.session_state:
    st.session_state.telegram_messages = pd.DataFrame()

# Keywords
flagged_words = ["drugs","cocaine","heroin","LSD","meth","weed","ganja","charas"]

# ML Detection
def detect_ml(msg):
    vec = vectorizer.transform([msg])
    return model.predict(vec)[0]

def hybrid_detection(msg):
    words = [w for w in flagged_words if w in msg.lower()]
    if words:
        return "Drug (Keyword) 🚨", words
    
    if detect_ml(msg) == 1:
        return "Drug (ML) 🚨", ["ML"]
    
    return "Normal ✅", []

# Menu
menu = option_menu("Menu", ["Home","Chat","Telegram","Statistics"])

# Home
if menu == "Home":
    st.title("AI Drug Detection System")

# Chat
elif menu == "Chat":
    st.title("Live Chat")

    msg = st.text_input("Enter message")

    if st.button("Send"):
        result, words = hybrid_detection(msg)

        if "Drug" in result:
            st.session_state.flagged_messages.append({
                "Message": msg,
                "Type": result,
                "Words": words
            })

        st.session_state.messages.append((msg, result))

    for m, r in st.session_state.messages:
        st.write(f"You: {m}")
        st.write(f"System: {r}")

# Telegram
elif menu == "Telegram":
    st.title("Telegram Monitor")

    api_id = 28192404
    api_hash = "YOUR_API_HASH"
    group = "sih150"

    client = TelegramClient("session", api_id, api_hash)

    async def fetch():
        async with client:
            data = []
            async for m in client.iter_messages(group, limit=50):
                text = m.text if m.text else ""
                result, words = hybrid_detection(text)

                data.append({
                    "Message": text,
                    "Result": result,
                    "Words": words
                })

            return pd.DataFrame(data)

    if st.button("Fetch"):
        try:
            df = asyncio.run(fetch())
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            df = loop.run_until_complete(fetch())

        st.session_state.telegram_messages = df

    if not st.session_state.telegram_messages.empty:
        st.dataframe(st.session_state.telegram_messages)

# Statistics
elif menu == "Statistics":
    st.title("Model Performance")

    st.write(f"Accuracy: {metrics['Accuracy']:.2f}")
    st.write(f"Precision: {metrics['Precision']:.2f}")
    st.write(f"Recall: {metrics['Recall']:.2f}")
    st.write(f"F1 Score: {metrics['F1 Score']:.2f}")

    st.bar_chart(metrics)

    if st.session_state.flagged_messages:
        df = pd.DataFrame(st.session_state.flagged_messages)
        st.write("Flagged Messages")
        st.dataframe(df)