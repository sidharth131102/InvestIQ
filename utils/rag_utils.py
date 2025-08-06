import os
import faiss
import numpy as np
import pickle
import streamlit as st
from utils.pdf_utils import extract_text_from_pdf
from models.embeddings import load_embedding_model

dimension = 384
index = faiss.IndexFlatL2(dimension)
documents = []  # now stores tuples: (chunk, filename)
indexed_files = set()

INDEX_PATH = "faiss_index/index.faiss"
DOCS_PATH = "faiss_index/documents.pkl"
FILES_PATH = "faiss_index/files.pkl"

def save_index():
    faiss.write_index(index, INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)
    with open(FILES_PATH, "wb") as f:
        pickle.dump(list(indexed_files), f)

@st.cache_resource
def load_index():
    global index, documents, indexed_files
    if os.path.exists(INDEX_PATH) and os.path.exists(DOCS_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(DOCS_PATH, "rb") as f:
            documents = pickle.load(f)
        if os.path.exists(FILES_PATH):
            with open(FILES_PATH, "rb") as f:
                indexed_files = set(pickle.load(f))

def build_knowledge_base(folder="knowledge_base"):
    """Rebuild knowledge base: only new PDFs."""
    embedder = load_embedding_model()
    for file in os.listdir(folder):
        if file.endswith(".pdf") and file not in indexed_files:
            file_path = os.path.join(folder, file)
            text = extract_text_from_pdf(file_path)
            chunks = [text[i:i+300] for i in range(0, len(text), 300)]
            add_to_index(chunks, embedder, source_file=file)
            indexed_files.add(file)
    save_index()

def add_to_index(chunks, embedder, source_file="Unknown"):
    global documents
    embeddings = embedder.encode(chunks)
    index.add(np.array(embeddings))
    documents.extend([(chunk, source_file) for chunk in chunks])

def retrieve(query, embedder, top_k=3):
    if len(documents) == 0:
        return [], []
    query_vector = embedder.encode([query])
    distances, indices = index.search(np.array(query_vector), top_k)
    results = []
    similarities = []
    for idx, dist in zip(indices[0], distances[0]):
        if idx < len(documents):
            chunk, filename = documents[idx]
            results.append((chunk, filename))
            similarities.append(1 - (dist**2)/2)
    return results, similarities
