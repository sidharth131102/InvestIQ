import re
from fpdf import FPDF
import os

def remove_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)  # keep only ASCII

def export_answer_to_pdf(query, answer, source, filename="chat_answer.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    query = remove_emojis(query)
    answer = remove_emojis(answer)
    source = remove_emojis(source)

    pdf.multi_cell(0, 10, "Qyora Chatbot Answer", align="C")
    pdf.ln(10)

    pdf.multi_cell(0, 10, f"Question: {query}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Answer: {answer}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Source: {source}")

    output_path = os.path.join("exports", filename)
    os.makedirs("exports", exist_ok=True)
    pdf.output(output_path)
    return output_path
