import pdfplumber
import camelot
import pandas as pd
from typing import List, Dict, Any
import logging

# Set up logging to suppress warnings
logging.getLogger('camelot').setLevel(logging.ERROR)

def extract_text_elements_pdfplumber(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text elements using pdfplumber for better structured extraction
    """
    all_elements = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            elements = []
            
            # Group characters into words and lines
            try:
                words = page.extract_words()
                word_elements = []
                
                for word in words:
                    # Safely extract coordinates with fallbacks
                    x0 = word.get("x0", 0)
                    y0 = word.get("y0", 0) 
                    x1 = word.get("x1", x0 + 50)  # fallback width
                    y1 = word.get("y1", y0 + 12)  # fallback height
                    
                    word_elements.append({
                        "text": word.get("text", "").strip(),
                        "bbox": [x0, y0, x1, y1],
                        "size": word.get("size", 12.0),
                        "font": word.get("fontname", "Unknown"),
                        "page": page_number + 1,
                        "type": "word"
                    })
            except Exception as e:
                print(f"Warning: Word extraction failed on page {page_number + 1}: {e}")
                word_elements = []
            
            all_elements.append({
                "page": page_number + 1,
                "elements": word_elements,
                "page_width": page.width,
                "page_height": page.height
            })
    
    return all_elements

def extract_tables_camelot(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables using Camelot for specialized table detection
    """
    try:
        # Use Camelot to extract tables
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        extracted_tables = []
        
        for i, table in enumerate(tables):
            # Convert to DataFrame for easier manipulation
            df = table.df
            
            # Clean empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Convert to list of lists
            table_data = df.values.tolist()
            
            extracted_tables.append({
                "table_id": i,
                "page": table.page,
                "accuracy": table.accuracy,
                "whitespace": table.whitespace,
                "data": table_data,
                "shape": df.shape,
                "bbox": [table._bbox[0], table._bbox[1], table._bbox[2], table._bbox[3]] if hasattr(table, '_bbox') else None
            })
            
        return extracted_tables
        
    except Exception as e:
        print(f"Camelot table extraction failed: {e}")
        return []

def extract_with_pdfplumber_camelot(pdf_path: str) -> Dict[str, Any]:
    """
    Combined extraction using both pdfplumber and Camelot
    """
    print(f"🔍 Extracting with pdfplumber + Camelot: {pdf_path}")
    
    # Extract text elements with pdfplumber
    text_elements = extract_text_elements_pdfplumber(pdf_path)
    
    # Extract tables with Camelot
    tables = extract_tables_camelot(pdf_path)
    
    # Combine results
    result = {
        "text_extraction": {
            "method": "pdfplumber",
            "pages": text_elements
        },
        "table_extraction": {
            "method": "camelot",
            "tables": tables,
            "table_count": len(tables)
        },
        "metadata": {
            "total_pages": len(text_elements),
            "total_tables_found": len(tables)
        }
    }
    
    return result


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys
    
    pdf_file = "../../invoices/Dummy_Invoice_Styled.pdf"
    if os.path.exists(pdf_file):
        # Test the new extraction method
        result = extract_with_pdfplumber_camelot(pdf_file)
        
        # Show results
        print(f"\n📄 Text Extraction Results:")
        for page in result['text_extraction']['pages']:
            print(f"Page {page['page']}: {len(page['elements'])} elements")
            
        print(f"\n📊 Table Extraction Results:")
        if result['table_extraction']['tables']:
            for table in result['table_extraction']['tables']:
                print(f"Table on page {table['page']}: {table['shape']} (accuracy: {table['accuracy']:.2f})")
                print("Sample data:", table['data'][:2] if table['data'] else "No data")
        else:
            print("No tables detected by Camelot")
            
        
    else:
        print(f"❌ File not found: {pdf_file}")
