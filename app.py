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
st.set_page_config(page_title="InvestIQ: Smarter Investing with AI", layout="wide")

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
    </style>
""", unsafe_allow_html=True)

# Title
st.title("InvestIQ: Smarter Investing with AI")
st.caption("Smart answers for smarter investments — Powered by Groq (Llama 4)")

start_time = time.time()

# Embedder caching
@st.cache_resource
def get_embedder():
    return load_embedding_model()

embedder = get_embedder()

# Sidebar
mode = st.sidebar.radio("Select Response Mode", ["Concise", "Detailed"])

st.sidebar.markdown("### Manage Session")
if st.sidebar.button("🗑️ Clear Queries"):
    pdf_text = st.session_state.get("uploaded_pdf_text")
    kb_loaded = st.session_state.get("kb_loaded", False)
    st.session_state.clear()
    if pdf_text:
        st.session_state["uploaded_pdf_text"] = pdf_text
    if kb_loaded:
        st.session_state["kb_loaded"] = kb_loaded
    st.rerun()

if st.sidebar.button("♻️ Clear All"):
    st.session_state.clear()
    st.rerun()

# Defaults
if "kb_loaded" not in st.session_state:
    st.session_state["kb_loaded"] = False
if "uploaded_pdf_text" not in st.session_state:
    st.session_state["uploaded_pdf_text"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "context" not in st.session_state:
    st.session_state["context"] = ""

# News & Trends cache
@st.cache_data(ttl=600)
def get_cached_news():
    return get_investment_news()

@st.cache_data(ttl=600)
def get_cached_trend(ticker):
    return plot_investment_trend(ticker)

# Sidebar News
st.sidebar.markdown("### 📰 Latest Investment News")
news_items, news_context = get_cached_news()
for title, url in news_items:
    st.sidebar.markdown(f"- [{title}]({url})")

# Sidebar Trends
st.sidebar.markdown("### 📊 Current Investment Trend")
ticker = st.sidebar.selectbox("Choose a stock/index:",
    ["^GSPC", "^NSEI", "AAPL", "GOOGL", "BTC-USD", "TSLA"])
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
    try:
        add_to_index(chunks, embedder, source_file=uploaded_file.name)
        save_index()
        st.session_state["kb_loaded"] = True
        st.success(f"✅ '{uploaded_file.name}' added to the Knowledge Base!")
    except Exception:
        st.warning("⚠️ Could not update Knowledge Base, will use PDF text directly.")

# Chat History
st.markdown("### 💬 Chat History")
for chat in st.session_state["chat_history"]:
    st.markdown(f"""
        <div class='chat-bubble'>
            <b>👤 You:</b> {chat['query']}<br>
            <b>🤖 InvestIQ:</b> {chat['answer']}<br>
            <small style='color:gray;'>Source: {chat['source']} • Confidence: {chat['confidence']}</small>
        </div>
    """, unsafe_allow_html=True)

# Query Input
with st.form(key='query_form', clear_on_submit=True):
    query = st.text_input("🔍 Ask a research question:")
    submit_button = st.form_submit_button(label='Submit')
# # Quick Ask Section
# st.markdown("### ⚡ Quick Ask")
# col1, col2, col3 = st.columns(3)

# user_query = None

# with col1:
#     if st.button("📈 Latest Market Trends"):
#         user_query = "What are the latest stock market trends today?"

# with col2:
#     if st.button("💡 Best Investment Tips"):
#         user_query = "Give me top investment tips for beginners."

# with col3:
#     if st.button("🌍 Global Market News"):
#         user_query = "What are the biggest global investment news updates?"


if submit_button and query:
    with st.spinner("InvestIQ is thinking..."):
        context, source, confidence_score, filename = "", "🌐 Groq Only", "N/A", "N/A"

        if not st.session_state["kb_loaded"]:
            try:
                load_index()
                build_knowledge_base()
                st.session_state["kb_loaded"] = True
            except Exception:
                st.session_state["kb_loaded"] = False

        if st.session_state["kb_loaded"]:
            context_chunks, similarities = retrieve(query, embedder)
            if context_chunks and similarities:
                highest_similarity = max(similarities)
                if highest_similarity > 0.50:
                    chunk_texts = [chunk for chunk, fname in context_chunks]
                    context = "\n".join(chunk_texts)
                    confidence_score = round(highest_similarity*100,2)
                    filename = context_chunks[0][1]
                    source = "🟣 Hybrid Answer (RAG)"

        if not context and st.session_state.get("trend_summary") and ticker.lower().split("-")[0] in query.lower():
            context = st.session_state["trend_summary"]
            source = "📊 Live Market Trend"
            confidence_score = 85.0

        if not context and ("news" in query.lower() or "market" in query.lower() or "investment" in query.lower()):
            if news_context:
                context = f"Latest investment headlines:\n{news_context}"
                source = "📰 Live Investment News"
                confidence_score = 80.0

        if not context:
            web_context = search_web(query)
            if web_context:
                context = web_context
                source = "🌐 Hybrid Answer (Web Search)"
                confidence_score = 70.0

        if not context and st.session_state.get("uploaded_pdf_text"):
            context = st.session_state["uploaded_pdf_text"][:1500]
            source = "📄 Uploaded PDF Fallback"
            confidence_score = "N/A"

        if context:
            prompt = f"Context:\n{context}\n\nQuestion: {query}"
            answer = get_groq_response(prompt, mode.lower())
        else:
            answer = get_groq_response(query, mode.lower())

        st.session_state["context"] = context
        st.session_state["chat_history"].append({
            "query": query, "answer": answer, "source": source,
            "confidence": confidence_score, "filename": filename
        })
        st.rerun()

# Context Preview
if st.session_state["context"] and st.session_state["chat_history"]:
    last_chat = st.session_state["chat_history"][-1]
    if any(x in last_chat["source"] for x in ["🟣 Hybrid Answer", "📄 Uploaded PDF Fallback", "📰 Live Investment News", "📊 Live Market Trend"]):
        st.markdown("**Context Used (Preview):**")
        preview = st.session_state["context"][:500]
        st.text_area("Preview", preview, height=200, disabled=True)
        # Show filename if available
        if "filename" in last_chat:
            st.caption(f"Source File: {last_chat['filename']}")


# Export to PDF
if st.session_state["chat_history"]:
    last_chat = st.session_state["chat_history"][-1]
    pdf_path = export_answer_to_pdf(
        query=last_chat["query"], answer=last_chat["answer"],
        source=last_chat["source"], filename="investiq_answer.pdf"
    )
    with open(pdf_path, "rb") as f:
        st.download_button("⬇️ Download Last Answer as PDF", f, "investiq_answer.pdf", "application/pdf")

st.sidebar.info(f"⏱️ App loaded in {time.time() - start_time:.2f} seconds")
