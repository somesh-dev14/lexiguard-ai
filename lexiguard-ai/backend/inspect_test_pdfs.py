import fitz
import os

pdf_names = [
    "LexiGuard_Test_Contract_Complete_Terms.pdf",
    "LexiGuard_Test_Contract_Missing_Terms.pdf",
    "lexiguard_sample_contract.pdf"
]

for name in pdf_names:
    path = os.path.join(r"C:\Users\warso\Downloads", name)
    if not os.path.exists(path):
        print(f"NOT FOUND: {path}")
        continue
    doc = fitz.open(path)
    print(f"\n==========================================")
    print(f"FILE: {name} (Pages: {len(doc)})")
    print(f"==========================================")
    for i, page in enumerate(doc):
        print(f"\n--- PAGE {i+1} ---")
        text = page.get_text()
        print(text)
