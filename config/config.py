import os

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL") # Use a robust model
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
RELEVANCE_THRESHOLD = 0.5 # A more accurate threshold (0.0 to 1.0)