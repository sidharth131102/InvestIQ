import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load model from .env, fallback to Llama 4 Scout if not set
MODEL_NAME =os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def get_groq_response(prompt, mode="concise"):
    sys_msg = "Provide a short, concise answer." if mode=="concise" else "Provide a detailed and comprehensive answer."
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()
