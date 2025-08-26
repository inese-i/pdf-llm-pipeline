"""
Clean Invoice Field Extractor
Regex-based field extraction for comparison with LLM approaches
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class InvoiceFields:
    """Structured invoice data"""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    vat_id: Optional[str] = None
    subtotal: Optional[str] = None
    vat_amount: Optional[str] = None
    total: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None


class InvoiceFieldExtractor:
    """Clean regex-based invoice field extractor"""
    
    def __init__(self):
        self.patterns = {
            'invoice_number': [
                r'(?:Invoice\s+(?:Number|No\.?)|Rechnungsnummer|Rechnung\s+Nr\.?):?\s*([A-Z0-9\-_/]+)',
                r'(?:Invoice|Rechnung)[\s\-#:]*([A-Z0-9\-_/]{3,})'
            ],
            'invoice_date': [
                r'(?:Invoice\s+Date|Rechnungsdatum):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})',
                r'(?:Date|Datum):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})'
            ],
            'due_date': [
                r'(?:Due\s+Date|Fälligkeitsdatum|Zahlbar\s+bis):?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})'
            ],
            'vat_id': [
                r'(?:VAT\s+ID|VATID|VAT-ID|USt-IdNr\.):?\s*([A-Z]{2}[A-Z0-9\s]{8,15})',
            ],
            'subtotal': [
                r'(?:Subtotal|Zwischensumme):?\s*([0-9.,]+)\s*€?',
            ],
            'vat_amount': [
                r'(?:VAT\s+Amount|USt\s+Betrag|MWST\s+Betrag|Umsatzsteuer):?\s*([0-9.,]+)\s*€?',
            ],
            'total': [
                r'(?:Total|Gesamtbetrag|Grand\s+Total):?\s*([0-9.,]+)\s*€?',
            ],
            'customer_name': [
                r'(?:Customer|Kunde|Bill\s+to):?\s*:?\s*([A-Za-z][A-Za-z\s&.,-]{5,50})',
            ],
            'iban': [
                r'IBAN:?\s*([A-Z]{2}[0-9]{2}[A-Z0-9\s]{4,32})',
            ],
            'bic': [
                r'BIC:?\s*([A-Z0-9]{8,11})',
            ],
            'bank_name': [
                r'Bank:?\s*([A-Za-z\s&.-]+(?:AG|GmbH|Bank)?)',
            ]
        }
    
    def extract_from_text(self, text: str) -> InvoiceFields:
        """Extract fields from combined text"""
        fields = InvoiceFields()
        
        for field_name, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Clean up the value
                    if field_name == 'iban':
                        value = value.replace(' ', '')
                    elif field_name in ['subtotal', 'vat_amount', 'total']:
                        value = value.replace(',', '.')
                    
                    setattr(fields, field_name, value)
                    break  # Use first match
        
        return fields
    
    def extract_from_pages(self, pages: List[Dict[str, Any]]) -> InvoiceFields:
        """Extract fields from page elements"""
        # Combine all text from pages
        combined_text = ""
        for page in pages:
            for element in page.get("elements", []):
                combined_text += " " + element.get("text", "")
        
        return self.extract_from_text(combined_text)
    
    def extract_from_chunks(self, chunks) -> InvoiceFields:
        """Extract fields from chunked content"""
        # Combine all chunk content
        combined_text = ""
        for chunk in chunks:
            combined_text += " " + chunk.content
        
        return self.extract_from_text(combined_text)
    
    def to_dict(self, fields: InvoiceFields) -> Dict[str, Any]:
        """Convert fields to dictionary"""
        return {
            field.name: getattr(fields, field.name)
            for field in fields.__dataclass_fields__.values()
            if getattr(fields, field.name) is not None
        }


# Simple interface functions for backward compatibility
def extract_invoice_metadata(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract basic invoice metadata"""
    extractor = InvoiceFieldExtractor()
    fields = extractor.extract_from_pages(pages)
    return {
        'vat_id': fields.vat_id,
        'subtotal': fields.subtotal,
        'vat_amount': fields.vat_amount,
        'total': fields.total
    }


def extract_bank_details(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract bank details"""
    extractor = InvoiceFieldExtractor()
    fields = extractor.extract_from_pages(pages)
    return {
        'iban': fields.iban,
        'bic': fields.bic,
        'bank_name': fields.bank_name
    }


# Test the extractor
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    Invoice Number: INV-2024-001
    Invoice Date: 15.08.2024
    Due Date: 30.08.2024
    VAT ID: DE123456789
    
    Customer: Test Customer GmbH
    
    Subtotal: 1,000.00 €
    VAT Amount: 190.00 €
    Total: 1,190.00 €
    
    IBAN: DE89 3704 0044 0532 0130 00
    BIC: COBADEFFXXX
    Bank: Commerzbank AG
    """
    
    extractor = InvoiceFieldExtractor()
    fields = extractor.extract_from_text(sample_text)
    
    print("🧪 Testing Clean Normalizer:")
    print("=" * 40)
    print(f"Invoice Number: {fields.invoice_number}")
    print(f"Date: {fields.invoice_date}")
    print(f"VAT ID: {fields.vat_id}")
    print(f"Total: {fields.total}")
    print(f"IBAN: {fields.iban}")
    print(f"Customer: {fields.customer_name}")
