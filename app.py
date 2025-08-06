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

# ---------------------- Page Config ----------------------
st.set_page_config(page_title="InvestIQ: Your Investment Assistant", layout="wide")

# ---------------------- Custom CSS ----------------------
st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d, #2e8b57);
        background-size: 400% 400%;
        animation: gradientBG 20s ease infinite;
    }
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .block-container {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(12px);
        border-radius: 18px;
        padding: 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        max-width: 950px;
        margin: auto;
    }
    h1 {
        font-weight: 800;
        text-align: center;
        color: #1a2a6c;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.25);
    }
    .chat-bubble {
        margin-bottom: 20px;
        border-radius: 16px;
        padding: 15px 20px;
        background: rgba(245, 248, 255, 0.9);
        box-shadow: 0 3px 12px rgba(0,0,0,0.15);
    }
    .chat-user { color: #163172; font-weight: bold; }
    .chat-bot { color: #0c5460; font-weight: bold; }
    div.stDownloadButton button {
        background: linear-gradient(90deg, #1a2a6c, #4a90e2);
        color: white;
        border-radius: 25px;
        font-size: 16px;
        padding: 12px 20px;
        border: none;
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
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1a2a6c;
    }
    </style>
""", unsafe_allow_html=True)


st.title("InvestIQ: Smarter Investing with AI")
st.caption("Smart answers for smarter investments — Powered by Groq (Llama 4)")

start_time = time.time()


@st.cache_resource
def get_embedder():
    return load_embedding_model()

embedder = get_embedder()

# ---------------------- Sidebar ----------------------
mode = st.sidebar.radio("Select Response Mode", ["Concise", "Detailed"])

st.sidebar.markdown("### 📰 Latest Investment News")
news_items, news_context = get_investment_news()
for title, url in news_items:
    st.sidebar.markdown(f"- [{title}]({url})")


st.sidebar.markdown("### 📊 Current Investment Trend")
ticker = st.sidebar.selectbox(
    "Choose a stock/index:",
    ["^GSPC", "^NSEI", "AAPL", "GOOGL", "BTC-USD", "TSLA"]
)
chart, trend_summary = plot_investment_trend(ticker)
if chart:
    st.sidebar.plotly_chart(chart, use_container_width=True)

# ---------------------- Quick Ask Buttons ----------------------
st.markdown("### 💡 Quick Ask")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📈 Market Overview"):
        st.session_state["quick_query"] = "Give me today's market overview."
with col2:
    if st.button("💰 Investment Strategies"):
        st.session_state["quick_query"] = "What are safe investment strategies for beginners?"
with col3:
    if st.button("🪙 Bitcoin Prediction"):
        st.session_state["quick_query"] = "What is the Bitcoin price prediction for the next quarter?"

# ---------------------- Chat History ----------------------
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

st.markdown("### 💬 Chat History")
for chat in st.session_state["chat_history"]:
    st.markdown(f"""
        <div class='chat-bubble'>
            <p class='chat-user'>👤 You:</p>
            <p>{chat['query']}</p>
            <hr style='border:0; border-top:1px solid #ddd;'>
            <p class='chat-bot'>🤖 InvestIQ:</p>
            <p>{chat['answer']}</p>
            <small style='color:gray;'>Source: {chat['source']} • Confidence: {chat['confidence']}</small>
        </div>
    """, unsafe_allow_html=True)

# ---------------------- Query Input ----------------------
with st.form(key='query_form', clear_on_submit=True):
    query = st.text_input("🔍 Ask a research question:", value=st.session_state.get("quick_query", ""))
    submit_button = st.form_submit_button(label='Submit')
    if "quick_query" in st.session_state:
        del st.session_state["quick_query"]

# ---------------------- Handle Query ----------------------
if submit_button and query:
    with st.spinner("InvestIQ is thinking..."):
        context = ""
        source = "🌐 Groq Only"
        confidence_score = "N/A"

        context_chunks, similarities = retrieve(query, embedder)
        if context_chunks:
            highest_similarity = max(similarities)
            if highest_similarity > 0.5:
                context = "\n".join([chunk for chunk, _ in context_chunks])
                source = "📚 Knowledge Base"
                confidence_score = round(highest_similarity * 100, 2)

        prompt = f"Context:\n{context}\n\nQuestion: {query}" if context else query
        answer = get_groq_response(prompt, mode.lower())

        # Typing animation
        placeholder = st.empty()
        typed = ""
        for char in answer:
            typed += char
            placeholder.markdown(f"<div class='chat-bubble'><p class='chat-bot'>🤖 {typed}</p></div>", unsafe_allow_html=True)
            time.sleep(0.015)

        st.session_state["chat_history"].append({
            "query": query,
            "answer": answer,
            "source": source,
            "confidence": confidence_score,
        })
        st.rerun()

# ---------------------- Export PDF ----------------------
if st.session_state["chat_history"]:
    last_chat = st.session_state["chat_history"][-1]
    filename_input = st.text_input("📄 Save PDF as:", "investiq_answer.pdf")
    if st.button("⬇️ Export Last Answer"):
        pdf_path = export_answer_to_pdf(
            query=last_chat["query"],
            answer=last_chat["answer"],
            source=last_chat["source"],
            filename=filename_input
        )
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download PDF",
                data=f,
                file_name=filename_input,
                mime="application/pdf"
            )

st.sidebar.info(f"⏱️ App loaded in {time.time() - start_time:.2f} seconds")
