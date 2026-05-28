import streamlit as st
import pandas as pd
import asyncio
import matplotlib.pyplot as plt
import re
from telethon.sync import TelegramClient
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import streamlit.components.v1 as components
# ================= PAGE CONFIG ================= #
st.set_page_config(page_title="AI Drug Dashboard", layout="wide")

st.markdown("""
    <style>
        .main {background-color: #0e1117; color: white;}
        .stDataFrame {background-color: #111827;}
        .card {
            padding: 20px;
            border-radius: 12px;
            background-color: #1f2937;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.5);
            margin: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("💊 AI Drug Monitoring Dashboard (LIVE)")

# ================= SESSION ================= #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["Message", "Name", "Username", "Mobile","Location", "Time", "Result", "Confidence"]
    )
if "last_time" not in st.session_state:
    st.session_state.last_time = None
# ================= LOGIN ================= #
def login_page():
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("✅ Login Successful")
            st.rerun()
        else:
            st.error("❌ Invalid Username or Password")

# ================= AI ================= #
ai_client = genai.Client(api_key="AIzaSyC1C22ZlKOEey_L1ub_ORkMaNuliQZMVj8")

# ================= TELEGRAM ================= #
api_id = 36179933
api_hash = "5a745c4bd3365b7add3c0a8815cd0c87"
tg_client = TelegramClient("session", api_id, api_hash)

# ================= NLP ================= #
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return text.strip()

df_data = pd.read_csv("drug_dataset_4000.csv")
df_data["Message"] = df_data["Message"].apply(clean_text)

vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
X = vectorizer.fit_transform(df_data["Message"])

model = MultinomialNB()
model.fit(X, df_data["Label"])

def get_location(sender, msg):
    # 📍 If user shared location
    if msg.geo:
        return f"📍 {msg.geo.lat}, {msg.geo.long}"

    # 🌍 If phone number available → country detect
    mobile = getattr(sender, "phone", None)

    if mobile:
        mobile = str(mobile)

        if mobile.startswith("91"):
            return "🌍 India"
        elif mobile.startswith("1"):
            return "🌍 USA"
        else:
            return "🌍 Other"

    return "❌ Not Available"
# ================= DETECT ================= #
def detect(msg):
    msg_clean = clean_text(msg)
    x = vectorizer.transform([msg_clean])

    prob = model.predict_proba(x)[0]
    confidence = max(prob) * 100
    pred = model.predict(x)[0]

    label = "🚨 Drug" if pred == 1 else "✅ Normal"
    return label, confidence

# ================= AI ================= #
def detect_ai(msg):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""
            Classify this message strictly as:
            - Drug
            - Normal

            Message: {msg}

            Only return one word: Drug or Normal
            """
        )

        text = response.text.lower()

        if "drug" in text or "suspicious" in text or "illegal" in text:
            return "🚨 Drug (AI)"
        else:
            return "✅ Normal (AI)"
         
    except:
        return None

# ================= TELEGRAM ================= #
def fetch_telegram_safe():
    
    messages = []

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        tg_client.connect()

        if not tg_client.is_user_authorized():
            tg_client.start()

        for msg in tg_client.iter_messages("groupnilesh", limit=60):

            if msg.message:
                sender = msg.sender

                name = ""
                username = ""
                mobile = "N/A"

                if sender:
                    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                    username = sender.username or "N/A"
                    mobile = getattr(sender, "phone", "N/A")

                location = get_location(sender, msg)

                messages.append({
                    "Message": msg.message,
                    "Name": name,
                    "Username": username,
                    "Mobile": mobile,
                    "Location": location,
                    "Time": str(msg.date)

                })

        tg_client.disconnect()

    except Exception as e:
        st.error(f"Telegram Error: {e}")

    return messages

# ================= MAIN ================= #
if not st.session_state.logged_in:
    login_page()
    st.stop()

st.sidebar.title("⚙️ Control Panel")

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

refresh = st.sidebar.button("🔄 Refresh Now")
auto_refresh = True

if refresh:
    st.rerun()

# ================= FETCH ================= #
placeholder = st.empty()
data = fetch_telegram_safe()
existing_keys = set(
        (row["Message"], row["Time"]) 
       for _, row in st.session_state.df.iterrows()
    ) if not st.session_state.df.empty else set()
existing_messages = set(st.session_state.df["Message"]) if not st.session_state.df.empty else set()
new_data = []

alerts = []

for item in data:
    msg = item["Message"]
    time_val = item["Time"]

    # 🔥 Skip only exact duplicate (Message + Time)
    if (msg, time_val) in existing_keys:
        continue

    # 🔥 ML prediction
    label, confidence = detect(msg)
    # 🔥 AI prediction (ALWAYS)
    ai_result = detect_ai(msg)

    # 🔥 FINAL DECISION (SIMPLE + STRONG)
    if ai_result:
        result = ai_result
    else:
        result = label

    # 🚨 Alert logic
    if "Drug" in result:
        alerts.append(f"🚨 {msg}")

    new_data.append({
        "Message": msg,
        "Name": item["Name"],
        "Username": item["Username"],
        "Mobile": item["Mobile"],
        "Location": item["Location"],
        "Time": item["Time"],
        "Result": result,
        "Confidence": round(confidence, 2)

    })

if new_data:
    new_df = pd.DataFrame(new_data)

    # 🔥 Remove empty rows
    new_df = new_df.dropna(how="all")

    # 🔥 Only proceed if valid data exists
    if not new_df.empty:

        # 🔥 If main df is empty → assign directly (NO CONCAT)
        if st.session_state.df.empty:
            st.session_state.df = new_df
        else:
            st.session_state.df = pd.concat(
                [st.session_state.df, new_df],
                ignore_index=True
            )

df = st.session_state.df
df = df.sort_values(by="Time", ascending=False)
if not df.empty:

# 🔥 Show message if no new data
    if not new_data:
        st.info("⏳ No new messages yet... Showing previous data")

# 🔥 Update last_time safely
if new_data:
    latest_time = max([item["Time"] for item in new_data])
    st.session_state.last_time = latest_time

# ================= AUTO REFRESH ================= #
    import time
    if auto_refresh:
        time.sleep(2)
        st.rerun()

# ================= ANALYTICS ================= #
st.markdown("Live Analytics")

if not st.session_state.df.empty:

    total = len(df)
    drugs = df["Result"].str.contains("🚨").sum()
    normal = total - drugs

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"<div class='card'><h3>Total</h3><h2>{total}</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'><h3>Drug</h3><h2>{drugs}</h2></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'><h3>Normal</h3><h2>{normal}</h2></div>", unsafe_allow_html=True)


if alerts:
    st.error(f"🚨 {len(alerts)} Drug Messages Detected!")
    # 🔊 SOUND ALERT
    components.html("""
        <audio autoplay>
        <source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3">
        </audio>
    """, height=0)
    for i, a in enumerate(alerts, 1):
        st.warning(f"{i}. {a}")

# ================= SEARCH + FILTER ================= #
st.markdown("## 🔍 Search & Filter")

search = st.text_input("Search Message / Username / Mobile")

filter_option = st.selectbox(
    "Filter",
    ["All", "🚨 Drug", "✅ Normal"]
)

filtered_df = df.copy()

if search:
    filtered_df = filtered_df[
        filtered_df["Message"].str.contains(search, case=False, na=False) |
        filtered_df["Username"].str.contains(search, case=False, na=False) |
        filtered_df["Mobile"].astype(str).str.contains(search, case=False, na=False)
    ]

if filter_option != "All":
    filtered_df = filtered_df[
        filtered_df["Result"].str.contains(filter_option)
    ]

# ================= TABLE ================= #
st.markdown("## 📩 Filtered Table")

st.dataframe(filtered_df, width="stretch", height=400)

# ================= CSV ================= #
csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "📥 Download CSV",
    csv,
    "filtered_data.csv",
    "text/csv"
)

# ================= GRAPH ================= #
st.markdown("## 📈 Live Updating Graph")

fig, ax = plt.subplots()

graph_df = filtered_df.copy()
graph_df["Result"] = graph_df["Result"].str.replace("🚨 ", "").str.replace("✅ ", "")

graph_df["Result"].value_counts().plot(kind="bar", ax=ax)

st.pyplot(fig)
