import fitz  # PyMuPDF

def extract_text_elements(pdf_path):
    doc = fitz.open(pdf_path)
    all_elements = []

    for page_number in range(len(doc)):
        page = doc[page_number]
        blocks = page.get_text("dict")["blocks"]
        elements = []

        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    elements.append({
                        "text": span["text"].strip(),
                        "bbox": span["bbox"],
                        "size": span["size"],
                        "font": span["font"],
                        "page": page_number + 1,
                        "type": "paragraph"  # Will refine in normalization
                    })

        all_elements.append({
            "page": page_number + 1,
            "elements": elements
        })

    return all_elements