import fitz  # PyMuPDF
from typing import List, Tuple
from app.schemas.document import PageText

class PDFExtractionError(Exception):
    pass

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[List[PageText], int, int]:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise PDFExtractionError(f"Failed to parse PDF: {str(e)}")

    pages: List[PageText] = []
    total_words = 0

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            word_count = len(text.split()) if text else 0
            total_words += word_count
            pages.append(PageText(page_number=page_idx + 1, text=text))
    finally:
        doc.close()

    return pages, len(pages), total_words
