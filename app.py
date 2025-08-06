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

# Load environment variables

# Page config
st.set_page_config(page_title="InvestIQ: Your Investment Assistant", layout="wide")

st.markdown("""
    <style>
    /* Background Gradient with Animation */
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

    /* Frosted Glass Effect for Main Container */
    .block-container {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.25);
        max-width: 900px;
        margin: auto;
    }

    /* Headings */
    h1 {
        color: #1a2a6c;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    h3 {
        color: #333;
        font-weight: 700;
        margin-bottom: 15px;
    }

    /* Chat Bubbles */
    .chat-bubble {
        margin-bottom: 20px;
        border-radius: 20px;
        padding: 15px 20px;
        background: linear-gradient(135deg, #f9f9f9, #e6f7ff);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .chat-user {
        color:#1a2a6c; font-weight:bold;
        margin-bottom: 5px;
    }
    .chat-bot {
        color:#0c5460; font-weight:bold;
        margin-bottom: 5px;
    }

    /* Stylish Download Button */
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

    /* Input Box Styling */
    .stTextInput > div > div > input {
        border: 2px solid #1a2a6c;
        border-radius: 12px;
        padding: 12px;
        font-size: 16px;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        font-size: 16px;
        font-weight: 600;
        color: #1a2a6c;
    }
    </style>
""", unsafe_allow_html=True)


st.title("📈 InvestIQ: Your One-Step Investing Assistant")
st.caption("Smart answers for smarter investments — Powered by Groq (Llama 4)")

start_time = time.time()

# Lazy-load embedder
@st.cache_resource
def get_embedder():
    return load_embedding_model()

embedder = get_embedder()

# Sidebar response mode
mode = st.sidebar.radio("Select Response Mode", ["Concise", "Detailed"])

# Sidebar cards
st.sidebar.markdown("""
    <div style='background:white;padding:15px;border-radius:15px;margin-bottom:20px;
                box-shadow:0 2px 10px rgba(0,0,0,0.1);'>
        <h3 style='color:#1a2a6c;'>📰 Latest Investment News</h3>
    </div>
""", unsafe_allow_html=True)

# Session management
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

# Session defaults
if "kb_loaded" not in st.session_state:
    st.session_state["kb_loaded"] = False
if "uploaded_pdf_text" not in st.session_state:
    st.session_state["uploaded_pdf_text"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "context" not in st.session_state:
    st.session_state["context"] = ""

# Cached news & trends
@st.cache_data(ttl=600)
def get_cached_news():
    return get_investment_news()

@st.cache_data(ttl=600)
def get_cached_trend(ticker):
    return plot_investment_trend(ticker)

# Sidebar: Latest news
news_items, news_context = get_cached_news()
for title, url in news_items:
    st.sidebar.markdown(f"- [{title}]({url})")

# Sidebar: Trend chart
st.sidebar.markdown("### 📊 Current Investment Trend")
ticker = st.sidebar.selectbox(
    "Choose a stock/index:",
    ["^GSPC", "^NSEI", "AAPL", "GOOGL", "BTC-USD", "TSLA"],
    index=0
)
chart, trend_summary = get_cached_trend(ticker)
if chart:
    st.sidebar.plotly_chart(chart, use_container_width=True)
    st.session_state["trend_summary"] = trend_summary
else:
    st.sidebar.warning("⚠️ Could not load investment trend chart.")
    st.session_state["trend_summary"] = ""

# PDF upload
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

# Chat history with styled bubbles
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

if submit_button and query:
    with st.spinner("InvestIQ is thinking..."):
        context = ""
        source = "🌐 Groq Only"
        confidence_score = "N/A"
        filename = "N/A"

        if not st.session_state["kb_loaded"]:
            try:
                load_index()
                build_knowledge_base()
                st.session_state["kb_loaded"] = True
            except Exception:
                st.session_state["kb_loaded"] = False

        context_chunks = []
        if st.session_state["kb_loaded"]:
            context_chunks, similarities = retrieve(query, embedder)
            if context_chunks and similarities:
                highest_similarity = max(similarities)
                if highest_similarity > 0.50:
                    chunk_texts = [chunk for chunk, fname in context_chunks]
                    context = "\n".join(chunk_texts)
                    confidence_score = highest_similarity
                    filename = context_chunks[0][1]
                    source = f"🟣 Hybrid Answer (RAG)"

        if not context and ticker.lower().split("-")[0] in query.lower():
            if st.session_state.get("trend_summary"):
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
            if "does not mention" in answer.lower() or "no information" in answer.lower():
                answer = get_groq_response(query, mode.lower())
                source = "🌐 Groq Only"
                confidence_score = "N/A"
                context = ""
        else:
            answer = get_groq_response(query, mode.lower())
            source = "🌐 Groq Only"

        st.session_state["context"] = context
        st.session_state["chat_history"].append({
            "query": query,
            "answer": answer,
            "source": source,
            "confidence": confidence_score,
            "filename": filename
        })
        st.rerun()

# Context preview
if st.session_state["context"] and st.session_state["chat_history"]:
    last_chat = st.session_state["chat_history"][-1]
    if any(x in last_chat["source"] for x in ["🟣 Hybrid Answer", "📄 Uploaded PDF Fallback", "📰 Live Investment News", "📊 Live Market Trend"]):
        with st.expander("📌 See Context Used"):
            st.markdown(f"""
                <div style='background:#f9f9f9;border-left:5px solid #1a2a6c;padding:15px;border-radius:10px;'>
                    <pre style='white-space:pre-wrap;font-family:monospace;'>{st.session_state['context'][:800]}</pre>
                </div>
            """, unsafe_allow_html=True)

# Export last answer with styled download button
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
