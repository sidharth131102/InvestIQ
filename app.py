import os
import time
import streamlit as st
from models.llm import get_groq_response
from models.embeddings import load_embedding_model
from utils.pdf_utils import extract_text_from_pdf
from utils.rag_utils import load_index, build_knowledge_base, add_to_index, save_index, retrieve
from utils.web_search import search_web
from utils.news import get_investment_news
from utils.finance import plot_investment_trend
from utils.pdf_export import export_answer_to_pdf

# Page config
st.set_page_config(page_title="InvestIQ: Your Investment Assistant", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    body {
        background: linear-gradient(270deg, #1a2a6c, #2e8b57, #b21f1f, #fdbb2d);
        background-size: 800% 800%;
        animation: gradientBG 20s ease infinite;
    }
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .block-container {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.25);
        max-width: 950px;
        margin: auto;
    }
    h1 {
        color: #1a2a6c;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .chat-bubble {
        margin-bottom: 20px;
        border-radius: 20px;
        padding: 15px 20px;
        background: linear-gradient(135deg, #f9f9f9, #e6f7ff);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .chat-user {color:#1a2a6c; font-weight:bold;}
    .chat-bot {color:#0c5460; font-weight:bold;}
    div.stDownloadButton button {
        background: linear-gradient(90deg, #1a2a6c, #4a90e2);
        color: white;
        border-radius: 30px;
        font-size: 18px;
        padding: 12px 24px;
        border: none;
        transition: all 0.3s ease;
    }
    div.stDownloadButton button:hover {
        background: linear-gradient(90deg, #163172, #2e8b57);
        transform: scale(1.05);
        color: #ffd700;
    }
    .stTextInput > div > div > input {
        border: 2px solid #1a2a6c;
        border-radius: 12px;
        padding: 12px;
        font-size: 16px;
    }
    .quick-ask-container {
        display: flex;
        justify-content: space-around;
        margin: 25px 0;
    }
    .quick-ask-button {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px 20px;
        color: #1a2a6c;
        font-size: 16px;
        font-weight: bold;
        border: 1px solid rgba(255,255,255,0.3);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        width: 30%;
    }
    .quick-ask-button:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.4);
        color: #2e8b57;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("📈 InvestIQ: Your One-Step Investing Assistant")
st.caption("Smart answers for smarter investments — Powered by Groq (Llama 4)")

start_time = time.time()

# Lazy-load embedder
@st.cache_resource
def get_embedder():
    return load_embedding_model()
embedder = get_embedder()

# Sidebar mode
mode = st.sidebar.radio("Select Response Mode", ["Concise", "Detailed"])

# Session management
if "kb_loaded" not in st.session_state:
    st.session_state["kb_loaded"] = False
if "uploaded_pdf_text" not in st.session_state:
    st.session_state["uploaded_pdf_text"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "context" not in st.session_state:
    st.session_state["context"] = ""

# News & trends
@st.cache_data(ttl=600)
def get_cached_news():
    return get_investment_news()
@st.cache_data(ttl=600)
def get_cached_trend(ticker):
    return plot_investment_trend(ticker)

# Sidebar: News
st.sidebar.markdown("### 📰 Latest Investment News")
news_items, news_context = get_cached_news()
for title, url in news_items:
    st.sidebar.markdown(f"- [{title}]({url})")

# Sidebar: Trend
st.sidebar.markdown("### 📊 Current Investment Trend")
ticker = st.sidebar.selectbox("Choose a stock/index:",
                              ["^GSPC", "^NSEI", "AAPL", "GOOGL", "BTC-USD", "TSLA"], index=0)
chart, trend_summary = get_cached_trend(ticker)
if chart:
    st.sidebar.plotly_chart(chart, use_container_width=True)
    st.session_state["trend_summary"] = trend_summary
else:
    st.sidebar.warning("⚠️ Could not load investment trend chart.")
    st.session_state["trend_summary"] = ""

# PDF Upload
st.markdown("### 📄 Optional: Add Your Own PDF")
uploaded_file = st.file_uploader("Upload a PDF to extend InvestIQ’s knowledge", type=["pdf"])
if uploaded_file:
    kb_path = os.path.join("knowledge_base", uploaded_file.name)
    with open(kb_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    text = extract_text_from_pdf(kb_path)
    st.session_state["uploaded_pdf_text"] = text
    chunks = [text[i:i+800] for i in range(0, len(text), 800)]
    add_to_index(chunks, embedder, source_file=uploaded_file.name)
    save_index()
    st.session_state["kb_loaded"] = True
    st.success(f"✅ '{uploaded_file.name}' added to the Knowledge Base!")

# Chat History
st.markdown("### 💬 Chat History")
for chat in st.session_state["chat_history"]:
    st.markdown(f"""
        <div class='chat-bubble'>
            <p class='chat-user'>👤 You:</p>
            <p>{chat['query']}</p>
            <hr style='border:0; border-top:1px solid #eee;'>
            <p class='chat-bot'>🤖 InvestIQ:</p>
            <p>{chat['answer']}</p>
            <small style='color:gray;'>Source: {chat['source']} • Confidence: {chat['confidence']}</small>
        </div>
    """, unsafe_allow_html=True)

# Query input
with st.form(key='query_form', clear_on_submit=True):
    query = st.text_input("🔍 Ask a research question:")
    submit_button = st.form_submit_button(label='Submit')

# Quick Ask buttons
st.markdown("""
    <div class="quick-ask-container">
        <form action="" method="post">
            <button type="submit" name="quick_query" value="What are the latest stock market trends today?" class="quick-ask-button">
                📈 Latest Market Trends
            </button>
            <button type="submit" name="quick_query" value="Give me top investment tips for beginners." class="quick-ask-button">
                💡 Best Investment Tips
            </button>
            <button type="submit" name="quick_query" value="What are the biggest global investment news updates?" class="quick-ask-button">
                🌍 Global Market News
            </button>
        </form>
    </div>
""", unsafe_allow_html=True)

# Process query or quick ask
if submit_button and query:
    user_query = query
elif "quick_query" in st.experimental_get_query_params():
    user_query = st.experimental_get_query_params()["quick_query"][0]
else:
    user_query = None

if user_query:
    with st.spinner("InvestIQ is thinking..."):
        context = ""
        source = "🌐 Groq Only"
        confidence_score = "N/A"
        filename = "N/A"

        if st.session_state["kb_loaded"]:
            context_chunks, similarities = retrieve(user_query, embedder)
            if context_chunks and similarities:
                context = "\n".join([chunk for chunk, _ in context_chunks])
                source = "🟣 Hybrid Answer (RAG)"
                confidence_score = round(max(similarities) * 100, 2)

        if not context:
            context = search_web(user_query) or ""
            if context:
                source = "🌐 Hybrid Answer (Web Search)"
                confidence_score = 70.0

        answer = get_groq_response(
            f"Context:\n{context}\n\nQuestion: {user_query}", mode.lower()
        ) if context else get_groq_response(user_query, mode.lower())

        st.session_state["context"] = context
        st.session_state["chat_history"].append({
            "query": user_query,
            "answer": answer,
            "source": source,
            "confidence": confidence_score,
            "filename": filename
        })
        st.experimental_rerun()

# Export PDF
if st.session_state["chat_history"]:
    last_chat = st.session_state["chat_history"][-1]
    pdf_path = export_answer_to_pdf(
        query=last_chat["query"],
        answer=last_chat["answer"],
        source=last_chat["source"],
        filename="investiq_answer.pdf"
    )
    with open(pdf_path, "rb") as f:
        st.download_button(
            label="⬇️ Download Last Answer as PDF",
            data=f,
            file_name="investiq_answer.pdf",
            mime="application/pdf"
        )

st.sidebar.info(f"⏱️ App loaded in {time.time() - start_time:.2f} seconds")
