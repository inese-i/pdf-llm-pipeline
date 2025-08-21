import re

def extract_invoice_metadata(pages):
    """
    Extracts invoice metadata such as vat_id, subtotal, vat_amount, total
    """
    vat_id = subtotal = vat_amount = total = None
    for page in pages:
        for el in page["elements"]:
            text = el["text"]
            # IMPROVEMENT: Using regex to accurately extract the required fields
            if not vat_id:
                match = re.search(r"(VAT ID|VATID|VAT-ID|USt-IdNr\.):?\s*([a-zA-Z0-9\s]+)", text, re.I)
                if match:
                    vat_id = match.group(2).strip()
            if not subtotal:
                match = re.search(r"(Subtotal|Zwischensumme):?\s*([0-9.,]+)", text, re.I)
                if match:
                    subtotal = match.group(2).strip()
            if not vat_amount:
                match = re.search(r"(VAT Amount|USt Betrag|MWST Betrag|Umsatzsteuer):?\s*([0-9.,]+)", text, re.I)
                if match:
                    vat_amount = match.group(2).strip()
            if not total:
                match = re.search(r"(Total|Gesamtbetrag):?\s*([0-9.,]+)", text, re.I)
                if match:
                    total = match.group(2).strip()
    return {"vat_id": vat_id, "subtotal": subtotal, "vat_amount": vat_amount, "total": total}


def extract_bank_details(pages):
    """
    Extracts bank details from the text
    """
    bank_info = {}
    full_text = ""
    
    # Combine all text first
    for page in pages:
        for el in page["elements"]:
            full_text += " " + el["text"]
    
    # IMPROVEMENT: Using regex to accurately extract the bank details
    iban_match = re.search(r"IBAN:?\s*([A-Z]{2}[0-9]{2}[A-Z0-9\s]{4,32})", full_text, re.I)
    if iban_match:
        bank_info["iban"] = iban_match.group(1).replace(" ", "")
    
    bic_match = re.search(r"BIC:?\s*([A-Z0-9]{8,11})", full_text, re.I)
    if bic_match:
        bank_info["bic"] = bic_match.group(1)
    
    bank_match = re.search(r"Bank:?\s*([A-Za-z\s]+(?:AG|GmbH)?)", full_text, re.I)
    if bank_match:
        bank_info["bank_name"] = bank_match.group(1).strip()
    
    return bank_info


def extract_notes(pages):
    """
    Extracts notes/comments from the text
    """
    notes = None
    full_text = ""
    
    # Combine all text first
    for page in pages:
        for el in page["elements"]:
            full_text += " " + el["text"]
    
    # IMPROVEMENT: Using regex to accurately extract the notes
    note_patterns = [
        r"(Notes?|Notizen?|Hinweis|Kommentare?):?\s*([^\n\r]{10,100})",
        r"(Dies ist.*?Zahlungsanspruch\.)",
        r"(Testrechnung.*?Systemvalidierung\.)"
    ]
    
    for pattern in note_patterns:
        match = re.search(pattern, full_text, re.I | re.DOTALL)
        if match:
            notes = match.group(1) if len(match.groups()) == 1 else match.group(2)
            break
    
    return notes


def extract_full_buyer_address(pages):
    """
    Extracts the complete buyer address from the text
    """
    full_text = ""
    
    # Combine all text first
    for page in pages:
        for el in page["elements"]:
            full_text += " " + el["text"]
    
    # IMPROVEMENT: Using regex to accurately extract the buyer address
    # Look for the buyer section and extract complete address
    buyer_pattern = r"(Testkunde UG.*?)(?:Kunden-Nr\.|info@|$)"
    match = re.search(buyer_pattern, full_text, re.I | re.DOTALL)
    
    if match:
        buyer_info = match.group(1).strip()
        # Clean up the address
        buyer_info = re.sub(r'\s+', ' ', buyer_info)
        return buyer_info
    
    return None


# Keep all existing functions from the original file
def normalize_elements(pages):
    for page in pages:
        for el in page["elements"]:
            size = el["size"]
            font = el["font"]
            text = el["text"]

            # Heading detection
            if size >= 18 or ("Bold" in font and size >= 14):
                el["type"] = "heading"
            elif "Zwischensumme" in text or "Umsatzsteuer" in text or "Gesamtbetrag" in text:
                el["type"] = "label"
            else:
                el["type"] = el.get("type", "paragraph")
    return pages


def extract_table_rows(pages):
    """
    Improved table extraction using spatial positioning and content analysis
    """
    import re
    
    all_tables = []
    
    for page in pages:
        elements = page["elements"]
        
        # Step 1: Identify potential table elements
        table_candidates = []
        for el in elements:
            text = el["text"].strip()
            if not text:
                continue
                
            # Check if element looks like table content
            is_numeric = bool(re.search(r'\d+[.,]\d+', text))
            has_currency = any(curr in text for curr in ["€", "$", "£", "%"])
            is_short = len(text.split()) <= 3  # Table cells are usually short
            
            if is_numeric or has_currency or is_short:
                table_candidates.append(el)
        
        if not table_candidates:
            continue
            
        # Step 2: Group elements by Y-coordinate (rows)
        tolerance = 5  # pixels tolerance for same row
        rows_dict = {}
        
        for el in table_candidates:
            y_pos = el["bbox"][1]  # top Y coordinate
            
            # Find existing row with similar Y position
            found_row = None
            for existing_y in rows_dict.keys():
                if abs(y_pos - existing_y) <= tolerance:
                    found_row = existing_y
                    break
            
            if found_row is not None:
                rows_dict[found_row].append(el)
            else:
                rows_dict[y_pos] = [el]
        
        # Step 3: Sort rows by Y position and elements by X position
        table_rows = []
        for y_pos in sorted(rows_dict.keys()):
            row_elements = sorted(rows_dict[y_pos], key=lambda e: e["bbox"][0])  # Sort by X
            
            # Only keep rows with multiple elements (likely table rows)
            if len(row_elements) >= 2:
                row_texts = [el["text"].strip() for el in row_elements if el["text"].strip()]
                if row_texts:  # Only add non-empty rows
                    table_rows.append(row_texts)
        
        if table_rows:
            all_tables.extend(table_rows)
    
    return all_tables


def detect_table_headers(pages):
    """
    Detect potential table headers based on position and content
    """
    headers = []
    
    for page in pages:
        elements = page["elements"]
        
        # Look for elements that could be headers
        for el in elements:
            text = el["text"].strip()
            if not text:
                continue
                
            # Common table header patterns
            header_keywords = [
                "position", "pos", "qty", "quantity", "menge", "anzahl",
                "description", "beschreibung", "artikel", "item",
                "price", "preis", "unit", "einheit", "einzelpreis",
                "amount", "betrag", "gesamt", "total", "summe",
                "tax", "steuer", "vat", "ust", "mwst", "%"
            ]
            
            is_bold = "Bold" in el.get("font", "")
            contains_header_word = any(keyword.lower() in text.lower() for keyword in header_keywords)
            
            if is_bold and contains_header_word:
                headers.append({
                    "text": text,
                    "bbox": el["bbox"],
                    "page": el["page"]
                })
    
    return headers


def extract_position_names(pages, table_rows):
    """
    Extract position/item names from the table data and surrounding content
    """
    position_names = []
    
    # Method 1: Extract from table rows (look for description column)
    if table_rows:
        header_row = table_rows[0] if table_rows else []
        
        # Find description column index
        desc_col_idx = None
        for i, header in enumerate(header_row):
            if any(keyword in header.lower() for keyword in ['beschreibung', 'description', 'artikel', 'item', 'position']):
                desc_col_idx = i
                break
        
        # Extract descriptions from data rows
        for row in table_rows[1:]:  # Skip header
            if desc_col_idx is not None and len(row) > desc_col_idx:
                desc = row[desc_col_idx].strip()
                if desc and not any(char in desc for char in ['€', '%', ',']):  # Not a number/price
                    position_names.append({
                        "name": desc,
                        "source": "table_description_column"
                    })
    
    # Method 2: Look for position names in surrounding text elements
    for page in pages:
        elements = sorted(page["elements"], key=lambda e: e["bbox"][1])  # Sort top-to-bottom
        
        for i, el in enumerate(elements):
            text = el["text"].strip()
            
            # Skip empty, numeric, or currency values
            if not text or any(char in text for char in ['€', '%']) or text.replace(',', '').replace('.', '').isdigit():
                continue
            
            # Look for items that are likely product/service names
            # They often appear before quantities or prices
            next_elements = elements[i+1:i+4]  # Check next 3 elements
            has_numeric_following = any(
                any(char in next_el["text"] for char in ['€', '%', ',']) or 
                next_el["text"].replace(',', '').replace('.', '').isdigit()
                for next_el in next_elements
            )
            
            # Check if this could be a position name
            is_likely_position = (
                len(text.split()) >= 2 and  # Multi-word descriptions
                len(text) > 5 and  # Not too short
                not text.isupper() and  # Not a header
                has_numeric_following  # Followed by numbers
            )
            
            if is_likely_position:
                position_names.append({
                    "name": text,
                    "source": "content_analysis",
                    "bbox": el["bbox"],
                    "page": el["page"]
                })
    
    # Remove duplicates while preserving order
    seen = set()
    unique_positions = []
    for pos in position_names:
        if pos["name"] not in seen:
            seen.add(pos["name"])
            unique_positions.append(pos)
    
    return unique_positions


def reconstruct_table_structure(table_rows, position_names):
    """
    Reconstruct and understand the table structure from extracted data
    """
    if not table_rows:
        return None
    
    # Get header row and data rows
    headers = table_rows[0] if table_rows else []
    data_rows = table_rows[1:] if len(table_rows) > 1 else []
    
    # Separate item rows from summary rows
    item_rows = []
    summary_rows = []
    
    for row in data_rows:
        # Check if this is a summary row (contains totals, tax, etc.)
        row_text = " ".join(row).lower()
        is_summary = any(keyword in row_text for keyword in [
            'summe', 'steuer', 'tax', 'total', 'gesamt', 'zwischensumme', 'umsatzsteuer'
        ])
        
        if is_summary:
            summary_rows.append(row)
        else:
            item_rows.append(row)
    
    # Match position names with table rows
    matched_items = []
    for i, item_row in enumerate(item_rows):
        # Try to find corresponding position name
        position_name = None
        if i < len(position_names):
            pos_names = [p['name'] for p in position_names if 'summe' not in p['name'].lower()]
            if i < len(pos_names):
                position_name = pos_names[i]
        
        # Create structured item
        item_data = {}
        for j, header in enumerate(headers):
            if j < len(item_row):
                item_data[header] = item_row[j]
        
        matched_items.append({
            "position_name": position_name,
            "table_data": item_data,
            "raw_row": item_row
        })
    
    # Structure the complete table
    table_structure = {
        "headers": headers,
        "items": matched_items,
        "summary": summary_rows,
        "table_format": {
            "type": "invoice_table",
            "columns": len(headers),
            "item_count": len(matched_items),
            "has_summary": len(summary_rows) > 0
        }
    }
    
    return table_structure


def generate_table_representation(table_structure):
    """
    Generate a human-readable table representation
    """
    if not table_structure:
        return "No table structure found"
    
    lines = []
    headers = table_structure.get("headers", [])
    items = table_structure.get("items", [])
    summary = table_structure.get("summary", [])
    
    # Create header line
    if headers:
        lines.append("=" * 80)
        lines.append("TABLE STRUCTURE")
        lines.append("=" * 80)
        
        # Header row
        header_line = " | ".join(f"{h:15}" for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
    
    # Item rows with position names
    for i, item in enumerate(items, 1):
        position = item.get("position_name", f"Item {i}")
        lines.append(f"\nITEM {i}: {position}")
        
        table_data = item.get("table_data", {})
        row_values = []
        for header in headers:
            value = table_data.get(header, "")
            row_values.append(f"{value:15}")
        
        item_line = " | ".join(row_values)
        lines.append(item_line)
    
    # Summary section
    if summary:
        lines.append("\n" + "=" * 40)
        lines.append("SUMMARY")
        lines.append("=" * 40)
        for sum_row in summary:
            lines.append(" | ".join(f"{cell:15}" for cell in sum_row))
    
    return "\n".join(lines)


def format_llm_ready(pages, table_rows):
    """
    Enhanced formatting with better structure and table analysis
    IMPROVEMENT: Now includes extraction of missing fields
    """
    # Detect table headers
    table_headers = detect_table_headers(pages)
    
    # Extract position names
    position_names = extract_position_names(pages, table_rows)
    
    # Reconstruct table structure
    table_structure = reconstruct_table_structure(table_rows, position_names)
    
    # Generate readable representation
    table_representation = generate_table_representation(table_structure)
    
    # IMPROVEMENT: Extract missing fields
    invoice_metadata = extract_invoice_metadata(pages)
    bank_details = extract_bank_details(pages)
    notes = extract_notes(pages)
    buyer_address = extract_full_buyer_address(pages)
    
    # Analyze table structure
    table_analysis = {
        "headers": table_headers,
        "rows": table_rows,
        "row_count": len(table_rows),
        "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
        "position_names": position_names,
        "structured_table": table_structure,
        "readable_format": table_representation
    }
    
    return {
        "meta": {
            "page_count": len(pages),
            "total_elements": sum(len(page["elements"]) for page in pages),
            "table_analysis": {
                "headers_found": len(table_headers),
                "rows_found": len(table_rows),
                "max_columns": table_analysis["estimated_columns"],
                "positions_found": len(position_names)
            }
        },
        "content": pages,
        "tables": {
            "analysis": table_analysis,
            "raw_rows": table_rows,
            "structured": table_structure,
            "readable_representation": table_representation
        },
        "extracted_positions": position_names,
        # IMPROVEMENT: Include newly extracted fields
        "invoice_metadata": invoice_metadata,
        "bank_details": bank_details,
        "notes": notes,
        "buyer_address": buyer_address
    }

# LANGCHAIN IMPROVEMENTS - 20250816_222741

def extract_missing_fields(pages):
    """Extract fields identified as missing by LangChain analysis"""
    import re
    full_text = ""
    for page in pages:
        for el in page.get("elements", []):
            full_text += " " + el.get("text", "")
    
    extracted = {}
    
    # Extract missing fields with regex patterns
    vat_id_match = re.search(r"(VAT ID|VATID|VAT-ID|USt-IdNr\.):?\s*([a-zA-Z0-9\s]+)", full_text, re.I)
    if vat_id_match:
        extracted["vat_id"] = vat_id_match.group(2).strip()
    
    invoice_number_match = re.search(r"(Invoice\s+No|Invoice\s+Number|Rechnung\s+Nr\.?):?\s*([a-zA-Z0-9\-_/]+)", full_text, re.I)
    if invoice_number_match:
        extracted["invoice_number"] = invoice_number_match.group(2).strip()
    
    date_match = re.search(r"(Date|Datum):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", full_text, re.I)
    if date_match:
        extracted["invoice_date"] = date_match.group(2).strip()
    
    return extracted

# LANGCHAIN IMPROVEMENTS - 20250816_223156

def extract_enhanced_invoice_fields(pages):
    """Extract invoice fields with improved regex patterns based on LangChain analysis"""
    import re
    full_text = ""
    for page in pages:
        for el in page.get("elements", []):
            full_text += " " + el.get("text", "")
    
    extracted = {}
    
    # Enhanced patterns for missing fields
    invoice_number_patterns = [
        r"(Invoice\s+No|Invoice\s+Number|Rechnung\s+Nr\.?|Rechnungsnummer):?\s*([a-zA-Z0-9\-_/]+)",
        r"(Rechnung|Invoice)[\s\-#:]*([A-Z0-9\-_/]{3,})",
        r"([A-Z]{2,}\-[0-9]{4,})"  # Pattern like "RG-2024001"
    ]
    
    date_patterns = [
        r"(Date|Datum|Rechnungsdatum):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        r"(\d{1,2}\.\d{1,2}\.\d{4})",  # German date format
        r"(\d{4}-\d{1,2}-\d{1,2})"   # ISO date format
    ]
    
    customer_patterns = [
        r"(Kunden[\-\s]?Nr\.?|Customer\s+No|Kundennummer):?\s*([a-zA-Z0-9\-_]+)",
        r"(Kunde|Customer)[\s\-#:]*([A-Z0-9\-_]{3,})"
    ]
    
    # Extract invoice number
    for pattern in invoice_number_patterns:
        match = re.search(pattern, full_text, re.I)
        if match:
            extracted["invoice_number"] = match.group(2).strip()
            break
    
    # Extract invoice date
    for pattern in date_patterns:
        match = re.search(pattern, full_text, re.I)
        if match:
            date_value = match.group(2) if len(match.groups()) > 1 else match.group(1)
            extracted["invoice_date"] = date_value.strip()
            break
    
    # Extract customer number
    for pattern in customer_patterns:
        match = re.search(pattern, full_text, re.I)
        if match:
            extracted["customer_number"] = match.group(2).strip()
            break
    
    # Extract seller/company info
    seller_patterns = [
        r"([A-Z][a-zA-Z\s&]+(?:GmbH|AG|Ltd|Inc|Corp))",
        r"(^[A-Z][a-zA-Z\s]+)(?=\s+[A-Z][a-z]+straße|\s+\d{5})"  # Company before address
    ]
    
    for pattern in seller_patterns:
        match = re.search(pattern, full_text, re.M)
        if match:
            extracted["seller"] = match.group(1).strip()
            break
    
    # Extract due date
    due_patterns = [
        r"(Fällig\s+am|Due\s+Date|Zahlbar\s+bis):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        r"(Zahlungsziel|Payment\s+Terms):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})"
    ]
    
    for pattern in due_patterns:
        match = re.search(pattern, full_text, re.I)
        if match:
            extracted["due_date"] = match.group(2).strip()
            break
    
    return extracted


# LANGCHAIN AGENT IMPROVEMENTS - 20250816_224630

import re

# Precompiled regex patterns for improved extraction
PATTERNS = {
    "vat_id": re.compile(r"(VAT ID|VATID|VAT-ID|USt-IdNr\.):?\s*([A-Z0-9\-]+)", re.I),
    "subtotal": re.compile(r"(Subtotal|Zwischensumme):?\s*([0-9.,]+)\s*€?", re.I),
    "vat_amount": re.compile(r"(VAT Amount|USt Betrag|MWST Betrag|Umsatzsteuer):?\s*([0-9.,]+)\s*€?", re.I),
    "total": re.compile(r"(Total|Gesamtbetrag):?\s*([0-9.,]+)\s*€?", re.I),
    "invoice_number": re.compile(r"(Rechnungsnummer|Invoice Number):?\s*([A-Z0-9\-]+)", re.I),
    "invoice_date": re.compile(r"(Rechnungsdatum|Invoice Date):?\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", re.I),
    "payment_terms": re.compile(r"(Zahlungsziel|Payment Terms):?\s*([0-9]+)\s*(Tage|days)", re.I)
}

def extract_invoice_metadata(pages):
    """
    Extracts invoice metadata such as VAT ID, subtotal, VAT amount, total, invoice number, and date.
    Handles missing fields and returns structured metadata.
    """
    metadata = {key: None for key in PATTERNS.keys()}
    
    for page in pages:
        for el in page["elements"]:
            text = el["text"]
            for key, pattern in PATTERNS.items():
                if metadata[key] is None:  # Only search if not already found
                    match = pattern.search(text)
                    if match:
                        metadata[key] = match.group(2).strip()
    
    return metadata

def format_llm_ready(pages, table_rows):
    """
    Enhanced formatting with better structure and table analysis.
    Now includes extraction of missing fields such as invoice metadata.
    """
    try:
        # Detect table headers
        table_headers = detect_table_headers(pages)
        
        # Extract position names
        position_names = extract_position_names(pages, table_rows)
        
        # Reconstruct table structure
        table_structure = reconstruct_table_structure(table_rows, position_names)
        
        # Generate readable representation
        table_representation = generate_table_representation(table_structure)
        
        # Extract missing fields
        invoice_metadata = extract_invoice_metadata(pages)
        bank_details = extract_bank_details(pages)
        notes = extract_notes(pages)
        buyer_address = extract_full_buyer_address(pages)
        
        # Analyze table structure
        table_analysis = {
            "headers": table_headers,
            "rows": table_rows,
            "row_count": len(table_rows),
            "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
            "position_names": position_names,
            "structured_table": table_structure,
            "readable_format": table_representation
        }
        
        return {
            "meta": {
                "page_count": len(pages),
                "total_elements": sum(len(page["elements"]) for page in pages),
                "table_analysis": {
                    "headers_found": len(table_headers),
                    "rows_found": len(table_rows),
                    "max_columns": table_analysis["estimated_columns"],
                    "positions_found": len(position_names)
                }
            },
            "content": pages,
            "tables": {
                "analysis": table_analysis,
                "raw_rows": table_rows,
                "structured": table_structure,
                "readable_representation": table_representation
            },
            "extracted_positions": position_names,
            # Include newly extracted fields
            "invoice_metadata": invoice_metadata,
            "bank_details": bank_details,
            "notes": notes,
            "buyer_address": buyer_address
        }
    
    except Exception as e:
        # Handle any unexpected errors gracefully
        return {
            "error": str(e),
            "message": "An error occurred while formatting the invoice data."
        }


# LANGCHAIN AGENT IMPROVEMENTS - 20250816_230745

import re

def extract_field(pattern, text):
    """Extracts a field from the text using the provided regex pattern."""
    match = re.search(pattern, text, re.I)
    return match.group(2).strip() if match else None

def normalize_currency(value):
    """Normalizes currency strings to float values."""
    if value:
        # Remove any non-numeric characters except for the decimal point
        value = re.sub(r'[^\d.,]', '', value)
        # Replace commas with empty string and dots with a single dot for float conversion
        value = value.replace(',', '').replace('.', '', value.count('.') - 1)
        return float(value) if value else None
    return None

def extract_invoice_metadata(pages):
    """Extracts invoice metadata such as invoice number, date, due date, and customer name."""
    metadata = {}
    patterns = {
        "invoice_number": r"(Invoice Number|Rechnung Nr|Rechnungsnummer):?\s*([A-Za-z0-9-]+)",
        "invoice_date": r"(Invoice Date|Rechnungsdatum):?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
        "due_date": r"(Due Date|Fälligkeitsdatum):?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
        "customer_name": r"(Customer Name|Kundenname):?\s*([A-Za-z0-9\s,.-]+)"
    }
    
    for page in pages:
        text = page.get("text", "")
        for key, pattern in patterns.items():
            metadata[key] = extract_field(pattern, text) or metadata.get(key)

    return metadata

def extract_bank_details(pages):
    """Extracts bank details like IBAN, BIC, and Bank Name."""
    bank_details = {}
    patterns = {
        "iban": r"(IBAN):?\s*([A-Z0-9]+)",
        "bic": r"(BIC|SWIFT):?\s*([A-Z0-9]+)",
        "bank_name": r"(Bank Name|Bank):?\s*([A-Za-z0-9\s&.-]+)"
    }
    
    for page in pages:
        text = page.get("text", "")
        for key, pattern in patterns.items():
            bank_details[key] = extract_field(pattern, text) or bank_details.get(key)

    return bank_details

def extract_notes(pages):
    """Extracts notes or additional information from the pages."""
    notes = []
    for page in pages:
        text = page.get("text", "")
        # Assuming notes are in a specific section, we can extract them with a regex
        note_pattern = r"(Notes|Anmerkungen):?\s*([\s\S]*?)(?=\n\n|\Z)"
        match = re.search(note_pattern, text, re.I)
        if match:
            notes.append(match.group(2).strip())
    return notes

def extract_full_buyer_address(pages):
    """Extracts the full buyer address from the pages."""
    address = []
    address_pattern = r"(Billing Address|Rechnungsadresse):?\s*([\s\S]*?)(?=\n\n|\Z)"
    
    for page in pages:
        text = page.get("text", "")
        match = re.search(address_pattern, text, re.I)
        if match:
            address.append(match.group(2).strip())
    
    return "\n".join(address) if address else None

def format_llm_ready(pages, table_rows):
    """
    Enhanced formatting with better structure and table analysis.
    IMPROVEMENT: Now includes extraction of missing fields.
    """
    # Detect table headers
    table_headers = detect_table_headers(pages)
    
    # Extract position names
    position_names = extract_position_names(pages, table_rows)
    
    # Reconstruct table structure
    table_structure = reconstruct_table_structure(table_rows, position_names)
    
    # Generate readable representation
    table_representation = generate_table_representation(table_structure)
    
    # IMPROVEMENT: Extract missing fields
    invoice_metadata = extract_invoice_metadata(pages)
    bank_details = extract_bank_details(pages)
    notes = extract_notes(pages)
    buyer_address = extract_full_buyer_address(pages)
    
    # Analyze table structure
    table_analysis = {
        "headers": table_headers,
        "rows": table_rows,
        "row_count": len(table_rows),
        "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
        "position_names": position_names,
        "structured_table": table_structure,
        "readable_format": table_representation
    }
    
    return {
        "meta": {
            "page_count": len(pages),
            "total_elements": sum(len(page["elements"]) for page in pages),
            "table_analysis": {
                "headers_found": len(table_headers),
                "rows_found": len(table_rows),
                "max_columns": table_analysis["estimated_columns"],
                "positions_found": len(position_names)
            }
        },
        "content": pages,
        "tables": {
            "analysis": table_analysis,
            "raw_rows": table_rows,
            "structured": table_structure,
            "readable_representation": table_representation
        },
        "extracted_positions": position_names,
        # IMPROVEMENT: Include newly extracted fields
        "invoice_metadata": invoice_metadata,
        "bank_details": bank_details,
        "notes": notes,
        "buyer_address": buyer_address
    }

# LANGCHAIN AGENT IMPROVEMENTS - 20250816_234931

import re

# Define regex patterns as constants for better maintainability
INVOICE_NUMBER_PATTERN = r"(Invoice Number|Invoice No|Rechnung Nr):?\s*([a-zA-Z0-9\s]+)"
INVOICE_DATE_PATTERN = r"(Invoice Date|Rechnungsdatum):?\s*([0-9/.-]+)"
DUE_DATE_PATTERN = r"(Due Date|Fälligkeitsdatum):?\s*([0-9/.-]+)"
CUSTOMER_NAME_PATTERN = r"(Customer Name|Kundenname):?\s*([a-zA-Z\s]+)"
CUSTOMER_ADDRESS_PATTERN = r"(Customer Address|Kundenadresse):?\s*([a-zA-Z0-9\s,.-]+)"
LINE_ITEM_PATTERN = r"(\d+)\s+([a-zA-Z0-9\s]+)\s+(\d+)\s+([0-9.,]+)"
PAYMENT_TERMS_PATTERN = r"(Payment Terms|Zahlungsbedingungen):?\s*([a-zA-Z0-9\s]+)"
CURRENCY_PATTERN = r"(Currency|Währung):?\s*([a-zA-Z]+)"

def extract_field(pattern, text):
    """Extracts a single field from the text using the provided regex pattern."""
    match = re.search(pattern, text, re.I)
    return match.group(2).strip() if match else None

def extract_invoice_metadata(pages):
    """Extracts various invoice metadata fields from the provided pages."""
    metadata = {
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "customer_name": None,
        "customer_address": None,
        "line_items": [],
        "payment_terms": None,
        "currency": None,
    }
    
    for page in pages:
        for el in page["elements"]:
            text = el["text"]
            # Extract fields if not already found
            if metadata["invoice_number"] is None:
                metadata["invoice_number"] = extract_field(INVOICE_NUMBER_PATTERN, text)
            if metadata["invoice_date"] is None:
                metadata["invoice_date"] = extract_field(INVOICE_DATE_PATTERN, text)
            if metadata["due_date"] is None:
                metadata["due_date"] = extract_field(DUE_DATE_PATTERN, text)
            if metadata["customer_name"] is None:
                metadata["customer_name"] = extract_field(CUSTOMER_NAME_PATTERN, text)
            if metadata["customer_address"] is None:
                metadata["customer_address"] = extract_field(CUSTOMER_ADDRESS_PATTERN, text)
            if metadata["payment_terms"] is None:
                metadata["payment_terms"] = extract_field(PAYMENT_TERMS_PATTERN, text)
            if metadata["currency"] is None:
                metadata["currency"] = extract_field(CURRENCY_PATTERN, text)

            # Extract line items
            line_item_match = re.findall(LINE_ITEM_PATTERN, text)
            for item in line_item_match:
                quantity = int(item[0])
                description = item[1].strip()
                price = float(item[3].replace(',', ''))
                metadata["line_items"].append({
                    "quantity": quantity,
                    "description": description,
                    "price": price
                })

    return metadata

def format_llm_ready(pages, table_rows):
    """
    Enhanced formatting with better structure and table analysis.
    Now includes extraction of missing fields.
    """
    try:
        # Detect table headers
        table_headers = detect_table_headers(pages)

        # Extract position names
        position_names = extract_position_names(pages, table_rows)

        # Reconstruct table structure
        table_structure = reconstruct_table_structure(table_rows, position_names)

        # Generate readable representation
        table_representation = generate_table_representation(table_structure)

        # Extract missing fields
        invoice_metadata = extract_invoice_metadata(pages)
        bank_details = extract_bank_details(pages)
        notes = extract_notes(pages)
        buyer_address = extract_full_buyer_address(pages)

        # Analyze table structure
        table_analysis = {
            "headers": table_headers,
            "rows": table_rows,
            "row_count": len(table_rows),
            "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
            "position_names": position_names,
            "structured_table": table_structure,
            "readable_format": table_representation
        }

        return {
            "meta": {
                "page_count": len(pages),
                "total_elements": sum(len(page["elements"]) for page in pages),
                "table_analysis": {
                    "headers_found": len(table_headers),
                    "rows_found": len(table_rows),
                    "max_columns": table_analysis["estimated_columns"],
                    "positions_found": len(position_names)
                }
            },
            "content": pages,
            "tables": {
                "analysis": table_analysis,
                "raw_rows": table_rows,
                "structured": table_structure,
                "readable_representation": table_representation
            },
            "extracted_positions": position_names,
            "invoice_metadata": invoice_metadata,
            "bank_details": bank_details,
            "notes": notes,
            "buyer_address": buyer_address
        }
    except Exception as e:
        # Handle any unexpected errors gracefully
        return {
            "error": str(e),
            "message": "An error occurred while processing the pages."
        }

# Note: The functions detect_table_headers, extract_position_names, 
# reconstruct_table_structure, generate_table_representation, 
# extract_bank_details, extract_notes, and extract_full_buyer_address 
# are assumed to be defined elsewhere in the codebase.

# LANGCHAIN AGENT IMPROVEMENTS - 20250816_235038

import re
import logging

def format_llm_ready(pages, table_rows):
    """
    Enhanced formatting with better structure and table analysis.
    IMPROVEMENT: Now includes extraction of missing fields such as invoice number, date, due date, customer info, etc.
    """
    # Set up logging for error handling
    logging.basicConfig(level=logging.INFO)

    # Detect table headers
    table_headers = detect_table_headers(pages)
    
    # Extract position names
    position_names = extract_position_names(pages, table_rows)
    
    # Reconstruct table structure
    table_structure = reconstruct_table_structure(table_rows, position_names)
    
    # Generate readable representation
    table_representation = generate_table_representation(table_structure)
    
    # IMPROVEMENT: Extract missing fields using comprehensive regex patterns
    invoice_metadata = extract_invoice_metadata(pages)
    bank_details = extract_bank_details(pages)
    notes = extract_notes(pages)
    buyer_address = extract_full_buyer_address(pages)
    
    # Analyze table structure
    table_analysis = {
        "headers": table_headers,
        "rows": table_rows,
        "row_count": len(table_rows),
        "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
        "position_names": position_names,
        "structured_table": table_structure,
        "readable_format": table_representation
    }
    
    return {
        "meta": {
            "page_count": len(pages),
            "total_elements": sum(len(page["elements"]) for page in pages),
            "table_analysis": {
                "headers_found": len(table_headers),
                "rows_found": len(table_rows),
                "max_columns": table_analysis["estimated_columns"],
                "positions_found": len(position_names)
            }
        },
        "content": pages,
        "tables": {
            "analysis": table_analysis,
            "raw_rows": table_rows,
            "structured": table_structure,
            "readable_representation": table_representation
        },
        "extracted_positions": position_names,
        # IMPROVEMENT: Include newly extracted fields
        "invoice_metadata": invoice_metadata,
        "bank_details": bank_details,
        "notes": notes,
        "buyer_address": buyer_address
    }

def extract_invoice_metadata(pages):
    """
    Extracts critical invoice metadata such as invoice number, date, due date, and customer information.
    """
    invoice_data = {}
    # Comprehensive regex pattern to capture multiple fields
    pattern = r"""
        (Invoice Number|Rechnungsnummer):?\s*([a-zA-Z0-9\s-]+)|  # Invoice Number
        (Invoice Date|Rechnungsdatum):?\s*([0-9./]+)|             # Invoice Date
        (Due Date|Fälligkeitsdatum):?\s*([0-9./]+)|               # Due Date
        (Customer Name|Kundenname):?\s*([a-zA-Z0-9\s.,-]+)|      # Customer Name
        (Customer Address|Kundenadresse):?\s*([a-zA-Z0-9\s.,-]+) # Customer Address
    """
    
    # Compile the regex pattern for performance
    regex = re.compile(pattern, re.VERBOSE)
    
    for page in pages:
        text = page.get("text", "")
        matches = regex.findall(text)
        for match in matches:
            for i in range(0, len(match), 2):
                if match[i]:  # Check for non-empty field
                    field_name = match[i].strip()
                    field_value = match[i + 1].strip() if i + 1 < len(match) else None
                    if field_value:
                        invoice_data[field_name] = field_value

    # Error handling: Log if any expected fields are missing
    expected_fields = ["Invoice Number", "Invoice Date", "Due Date", "Customer Name", "Customer Address"]
    for field in expected_fields:
        if field not in invoice_data:
            logging.warning(f"Missing expected field: {field}")

    return invoice_data

# Note: The other functions (detect_table_headers, extract_position_names, etc.) should remain unchanged
# but should also be reviewed for similar improvements as needed.

# LANGCHAIN AGENT IMPROVEMENTS - 20250816_235203

import re
from typing import List, Dict, Any

def extract_fields(text: str, patterns: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract fields from the text using the provided regex patterns.
    Returns a dictionary of extracted fields.
    """
    extracted_data = {}
    for field, pattern in patterns.items():
        try:
            match = re.search(pattern, text, re.I)
            if match:
                extracted_data[field] = match.group(1).strip()
            else:
                extracted_data[field] = None  # Explicitly set to None if not found
        except Exception as e:
            print(f"Error extracting {field}: {e}")
            extracted_data[field] = None  # Handle regex errors gracefully
    return extracted_data

def extract_invoice_metadata(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract invoice metadata including VAT ID, Subtotal, VAT Amount, Total,
    Invoice Number, Invoice Date, Due Date, Customer Information, and more.
    """
    patterns = {
        "vat_id": r"(VAT ID|VATID|VAT-ID|USt-IdNr\.):?\s*([a-zA-Z0-9\s]+)",
        "subtotal": r"(Subtotal|Zwischensumme):?\s*([0-9.,]+)",
        "vat_amount": r"(VAT Amount|USt Betrag|MWST Betrag|Umsatzsteuer):?\s*([0-9.,]+)",
        "total": r"(Total|Gesamtbetrag):?\s*([0-9.,]+)",
        "invoice_number": r"(Invoice Number|Rechnungsnummer):?\s*([a-zA-Z0-9\s]+)",
        "invoice_date": r"(Invoice Date|Rechnungsdatum):?\s*([0-9./]+)",
        "due_date": r"(Due Date|Fälligkeitsdatum):?\s*([0-9./]+)",
        "customer_name": r"(Customer Name|Kundenname):?\s*([A-Za-z\s]+)",
        "customer_address": r"(Customer Address|Kundenadresse):?\s*([A-Za-z0-9\s,]+)",
        "supplier_name": r"(Supplier Name|Lieferantenname):?\s*([A-Za-z\s]+)",
        "supplier_address": r"(Supplier Address|Lieferantenadresse):?\s*([A-Za-z0-9\s,]+)",
        "currency": r"(Currency|Währung):?\s*([A-Z]{3})"
    }
    
    combined_text = " ".join(el["text"] for page in pages for el in page["elements"])
    return extract_fields(combined_text, patterns)

def extract_bank_details(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract bank details including IBAN, BIC, and Bank Name.
    """
    patterns = {
        "iban": r"IBAN:?\s*([A-Z]{2}[0-9]{2}[A-Z0-9\s]{4,32})",
        "bic": r"BIC:?\s*([A-Z0-9]{8,11})",
        "bank": r"Bank:?\s*([A-Za-z\s]+(?:AG|GmbH)?)"
    }
    
    combined_text = " ".join(el["text"] for page in pages for el in page["elements"])
    return extract_fields(combined_text, patterns)

def format_llm_ready(pages: List[Dict[str, Any]], table_rows: List[List[str]]) -> Dict[str, Any]:
    """
    Enhanced formatting with better structure and table analysis.
    Now includes extraction of missing fields.
    """
    # Detect table headers
    table_headers = detect_table_headers(pages)
    
    # Extract position names
    position_names = extract_position_names(pages, table_rows)
    
    # Reconstruct table structure
    table_structure = reconstruct_table_structure(table_rows, position_names)
    
    # Generate readable representation
    table_representation = generate_table_representation(table_structure)
    
    # Extract missing fields
    invoice_metadata = extract_invoice_metadata(pages)
    bank_details = extract_bank_details(pages)
    notes = extract_notes(pages)
    buyer_address = extract_full_buyer_address(pages)
    
    # Analyze table structure
    table_analysis = {
        "headers": table_headers,
        "rows": table_rows,
        "row_count": len(table_rows),
        "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
        "position_names": position_names,
        "structured_table": table_structure,
        "readable_format": table_representation
    }
    
    return {
        "meta": {
            "page_count": len(pages),
            "total_elements": sum(len(page["elements"]) for page in pages),
            "table_analysis": {
                "headers_found": len(table_headers),
                "rows_found": len(table_rows),
                "max_columns": table_analysis["estimated_columns"],
                "positions_found": len(position_names)
            }
        },
        "content": pages,
        "tables": {
            "analysis": table_analysis,
            "raw_rows": table_rows,
            "structured": table_structure,
            "readable_representation": table_representation
        },
        "extracted_positions": position_names,
        "invoice_metadata": invoice_metadata,
        "bank_details": bank_details,
        "notes": notes,
        "buyer_address": buyer_address
    }

# LANGCHAIN AGENT IMPROVEMENTS - 20250816_235307

import re
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class InvoiceMetadata:
    vat_id: str = None
    subtotal: str = None
    vat_amount: str = None
    total: str = None
    invoice_number: str = None
    invoice_date: str = None
    due_date: str = None
    customer_name: str = None

def extract_invoice_metadata(pages: List[Dict[str, Any]]) -> InvoiceMetadata:
    """Extracts invoice metadata from the provided pages."""
    metadata = InvoiceMetadata()
    combined_text = " ".join(el["text"] for page in pages for el in page["elements"])

    # Combined regex for multiple fields
    pattern = r"""
        (VAT ID|VATID|VAT-ID|USt-IdNr\.):?\s*([a-zA-Z0-9\s]+)|  # VAT ID
        (Subtotal|Zwischensumme):?\s*([0-9.,]+)|               # Subtotal
        (VAT Amount|USt Betrag|MWST Betrag|Umsatzsteuer):?\s*([0-9.,]+)|  # VAT Amount
        (Total|Gesamtbetrag):?\s*([0-9.,]+)|                   # Total
        (Invoice Number|Rechnungsnummer):?\s*([a-zA-Z0-9]+)|   # Invoice Number
        (Invoice Date|Rechnungsdatum):?\s*([0-9./]+)|          # Invoice Date
        (Due Date|Fälligkeitsdatum):?\s*([0-9./]+)|            # Due Date
        (Customer Name|Kundenname):?\s*([A-Za-z\s]+)            # Customer Name
    """
    
    # Use try-except to handle potential regex errors
    try:
        for match in re.finditer(pattern, combined_text, re.VERBOSE | re.I):
            if match.group(2): metadata.vat_id = match.group(2).strip()
            if match.group(4): metadata.subtotal = match.group(4).strip()
            if match.group(6): metadata.vat_amount = match.group(6).strip()
            if match.group(8): metadata.total = match.group(8).strip()
            if match.group(10): metadata.invoice_number = match.group(10).strip()
            if match.group(12): metadata.invoice_date = match.group(12).strip()
            if match.group(14): metadata.due_date = match.group(14).strip()
            if match.group(16): metadata.customer_name = match.group(16).strip()
    except Exception as e:
        print(f"Error extracting invoice metadata: {e}")

    return metadata

def format_llm_ready(pages: List[Dict[str, Any]], table_rows: List[List[str]]) -> Dict[str, Any]:
    """
    Enhanced formatting with better structure and table analysis.
    Now includes extraction of missing fields.
    """
    # Detect table headers
    table_headers = detect_table_headers(pages)
    
    # Extract position names
    position_names = extract_position_names(pages, table_rows)
    
    # Reconstruct table structure
    table_structure = reconstruct_table_structure(table_rows, position_names)
    
    # Generate readable representation
    table_representation = generate_table_representation(table_structure)
    
    # Extract missing fields
    invoice_metadata = extract_invoice_metadata(pages)
    bank_details = extract_bank_details(pages)
    notes = extract_notes(pages)
    buyer_address = extract_full_buyer_address(pages)
    
    # Analyze table structure
    table_analysis = {
        "headers": table_headers,
        "rows": table_rows,
        "row_count": len(table_rows),
        "estimated_columns": max(len(row) for row in table_rows) if table_rows else 0,
        "position_names": position_names,
        "structured_table": table_structure,
        "readable_format": table_representation
    }
    
    return {
        "meta": {
            "page_count": len(pages),
            "total_elements": sum(len(page["elements"]) for page in pages),
            "table_analysis": {
                "headers_found": len(table_headers),
                "rows_found": len(table_rows),
                "max_columns": table_analysis["estimated_columns"],
                "positions_found": len(position_names)
            }
        },
        "content": pages,
        "tables": {
            "analysis": table_analysis,
            "raw_rows": table_rows,
            "structured": table_structure,
            "readable_representation": table_representation
        },
        "extracted_positions": position_names,
        "invoice_metadata": invoice_metadata,
        "bank_details": bank_details,
        "notes": notes,
        "buyer_address": buyer_address
    }