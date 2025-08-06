import streamlit as st
from groq import Groq

# ✅ Load Groq API key from Streamlit secrets
try:
    api_key = st.secrets["GROQ_API_KEY"]
except KeyError:
    raise ValueError("❌ GROQ_API_KEY not found. Please add it in Streamlit Cloud → Settings → Secrets.")

# ✅ Initialize Groq client
client = Groq(api_key=api_key)

# ✅ Define model (you can override via Streamlit secrets if needed)
MODEL_NAME = st.secrets.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

def get_groq_response(prompt, mode="concise"):
    """
    Get a response from Groq (Llama 4).
    Mode can be 'concise' or 'detailed'.
    """
    sys_msg = "Provide a short, concise answer." if mode == "concise" else "Provide a detailed and comprehensive answer."
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500 if mode == "concise" else 1000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Groq API error: {str(e)}"
