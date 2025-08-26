#!/usr/bin/env python3
"""
Spatial Invoice Chunker - Uses PDF extraction coordinates for intelligent chunking
Leverages existing pdfplumber + Camelot extraction for natural invoice sections
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
import re

@dataclass
class InvoiceChunk:
    content: str
    chunk_type: str  # 'header', 'vendor', 'customer', 'line_items', 'totals', 'payment'
    elements: List[Dict]  # Original PDF elements
    bbox: Tuple[float, float, float, float]  # Combined bounding box
    page_number: int
    confidence: float  # How confident we are in the chunk type

class SpatialInvoiceChunker:
    """
    Adaptive spatial invoice chunker that handles different invoice layouts
    by using content patterns + spatial hints rather than fixed positions.
    """
    
    def __init__(self):
        self.chunk_types = ['header', 'addresses', 'line_items', 'totals', 'footer']
        
        # Content patterns that indicate chunk types (layout-agnostic)
        self.content_patterns = {
            'header': [
                r'invoice\s*#?\s*\d+',
                r'bill\s*#?\s*\d+', 
                r'date\s*:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'invoice\s*date',
                r'due\s*date'
            ],
            'addresses': [
                r'bill\s*to\s*:?',
                r'ship\s*to\s*:?',
                r'sold\s*to\s*:?',
                r'customer\s*:?',
                r'\d+\s+[a-z\s]+\s+(st|ave|rd|blvd|drive|lane)',  # Address patterns
                r'[a-z\s]+,\s*[a-z]{2}\s*\d{5}'  # City, State ZIP
            ],
            'line_items': [
                r'description',
                r'quantity|qty',
                r'price|rate|amount',
                r'item\s*#?',
                r'product',
                r'service'
            ],
            'totals': [
                r'subtotal|sub\s*total',
                r'tax|vat',
                r'total|grand\s*total',
                r'amount\s*due',
                r'balance',
                r'discount'
            ]
        }
        
    def chunk_invoice_spatially(self, pages: List[Dict], tables: List[Dict]) -> List[InvoiceChunk]:
        """Create adaptive spatial chunks that work across different invoice layouts"""
        chunks = []
        
        for page_num, page in enumerate(pages):
            elements = page.get('elements', [])
            
            # Use content + spatial analysis for adaptive grouping
            adaptive_groups = self._adaptive_spatial_grouping(elements)
            
            # Create chunks from adaptive groups
            for region_type, group_elements in adaptive_groups.items():
                if group_elements:
                    chunk = self._create_chunk_from_elements(
                        group_elements, region_type, page_num + 1
                    )
                    chunks.append(chunk)
        
        # Add table chunks (tables are usually line items)
        for table in tables:
            table_chunk = self._create_table_chunk(table)
            chunks.append(table_chunk)
        
        return chunks
    
    def _adaptive_spatial_grouping(self, elements: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Adaptive grouping that uses BOTH content patterns AND spatial hints
        to handle different invoice layouts intelligently.
        """
        groups = {chunk_type: [] for chunk_type in self.chunk_types}
        
        # Sort elements by y-coordinate (top to bottom)
        sorted_elements = sorted(elements, key=lambda e: e.get('bbox', [0,0,0,0])[1], reverse=True)
        
        # Separate totals first (they often have specific patterns)
        totals_elements = []
        other_elements = []
        
        for element in sorted_elements:
            text = element.get('text', '').lower()
            
            # Look for total/sum patterns
            if any(pattern in text for pattern in ['gesamt', 'total', 'summe', 'betrag', 'steuer', 'mwst', 'ust']):
                totals_elements.append(element)
            # Look for money amounts (likely totals)
            elif re.search(r'\d+[,.]\d+\s*€', text) and any(word in text for word in ['€']):
                # Check if it's likely a total (not just a line item price)
                bbox = element.get('bbox', [0,0,0,0])
                if bbox[0] > 400:  # Right side of page, likely totals
                    totals_elements.append(element)
                else:
                    other_elements.append(element)
            else:
                other_elements.append(element)
        
        # Process totals elements
        groups['totals'] = totals_elements
        
        # Process remaining elements
        for element in other_elements:
            text = element.get('text', '').lower()
            bbox = element.get('bbox', [0, 0, 0, 0])
            font_info = element.get('font_info', {})
            y_position = bbox[1] if bbox else 0
            
            # Determine chunk type using content patterns + spatial context
            chunk_type = self._classify_element_adaptively(element, text, bbox, font_info)
            groups[chunk_type].append(element)
        
        return groups
    
    def _classify_element_adaptively(self, element: Dict, text: str, bbox: List, font_info: Dict) -> str:
        """Classify element using content patterns + spatial/visual clues"""
        y_position = bbox[1] if bbox else 0
        font_size = font_info.get('size', 10)
        
        # Check content patterns for each chunk type
        for chunk_type, patterns in self.content_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return chunk_type
        
        # Use spatial/visual clues as backup
        # Header: Usually top of page, larger font
        if y_position > 700 and font_size > 12:  # Top area, large font
            return 'header'
        
        # Totals: Usually bottom right, contains numbers
        elif y_position < 200 and re.search(r'\$[\d,]+\.?\d*', text):  # Bottom area with money
            return 'totals'
        
        # Line items: Middle area, structured data
        elif 200 < y_position < 700 and re.search(r'\d+\.\d{2}|\d+\s*x\s*\d+', text):
            return 'line_items'
        
        # Addresses: Usually upper-middle, contains address patterns
        elif y_position > 500 and re.search(r'\d+\s+[a-z\s]+(st|ave|rd|blvd)', text, re.IGNORECASE):
            return 'addresses'
        
        # Default fallback
        return 'header' if y_position > 400 else 'footer'
    
    def _create_chunk_from_elements(self, elements: List[Dict], chunk_type: str, page_num: int) -> InvoiceChunk:
        """Create a chunk from grouped elements"""
        combined_text = '\n'.join([elem.get('text', '') for elem in elements])
        
        # Calculate bounding box for the entire chunk
        bboxes = [elem.get('bbox', [0,0,0,0]) for elem in elements if elem.get('bbox')]
        if bboxes:
            min_x = min(bbox[0] for bbox in bboxes)
            min_y = min(bbox[1] for bbox in bboxes)  
            max_x = max(bbox[2] for bbox in bboxes)
            max_y = max(bbox[3] for bbox in bboxes)
            chunk_bbox = [min_x, min_y, max_x, max_y]
        else:
            chunk_bbox = [0, 0, 0, 0]
        
        # Extract metadata
        metadata = {
            'element_count': len(elements),
            'bbox': chunk_bbox,
            'fonts': list(set(elem.get('font_info', {}).get('name', 'unknown') for elem in elements)),
            'avg_font_size': np.mean([elem.get('font_info', {}).get('size', 10) for elem in elements])
        }
        
        return InvoiceChunk(
            content=combined_text,
            chunk_type=chunk_type,
            elements=elements,
            bbox=(float(chunk_bbox[0]), float(chunk_bbox[1]), float(chunk_bbox[2]), float(chunk_bbox[3])),
            page_number=page_num,
            confidence=0.8  # Default confidence
        )
    
    def _create_table_chunk(self, table: Dict) -> InvoiceChunk:
        """Create chunk from table data with LLM-readable format"""
        table_text = ""
        
        if 'data' in table and table['data']:
            # Create a structured table format that LLMs can easily parse
            rows = table['data']
            
            # Add table header context
            table_text += "TABLE: Invoice Line Items\n"
            table_text += "=" * 50 + "\n"
            
            # Process each row with clear structure
            for i, row in enumerate(rows, 1):
                if len(row) >= 2:
                    description = str(row[0]) if row[0] else ""
                    details = str(row[1]) if row[1] else ""
                    
                    # Parse the details column that contains quantity, price, tax, total
                    parsed_details = self._parse_line_item_details(details)
                    
                    table_text += f"LINE ITEM {i}:\n"
                    table_text += f"  Description: {description}\n"
                    table_text += f"  Quantity: {parsed_details.get('quantity', 'N/A')}\n"
                    table_text += f"  Unit: {parsed_details.get('unit', 'N/A')}\n"
                    table_text += f"  Unit Price: {parsed_details.get('unit_price', 'N/A')}\n"
                    table_text += f"  Tax Rate: {parsed_details.get('tax_rate', 'N/A')}\n"
                    table_text += f"  Line Total: {parsed_details.get('line_total', 'N/A')}\n"
                    table_text += "-" * 30 + "\n"
        
        return InvoiceChunk(
            content=table_text,
            chunk_type='line_items',
            elements=[],
            bbox=(float(table.get('bbox', [0,0,0,0])[0]), float(table.get('bbox', [0,0,0,0])[1]), 
                  float(table.get('bbox', [0,0,0,0])[2]), float(table.get('bbox', [0,0,0,0])[3])),
            page_number=table.get('page', 1),
            confidence=0.9
        )
    
    def _parse_line_item_details(self, details_text: str) -> Dict[str, str]:
        """Parse the details column to extract structured information"""
        parsed = {}
        
        # Split by newlines and clean up
        lines = [line.strip() for line in details_text.split('\n') if line.strip()]
        
        for line in lines:
            # Look for quantity patterns like "10,00" at start
            if re.match(r'^\d+[,.]?\d*$', line):
                parsed['quantity'] = line
            
            # Look for units like "Std.", "Stk."
            elif re.match(r'^(Std\.|Stk\.|St\.|Stück|Hours?|pcs?)\.?$', line, re.IGNORECASE):
                parsed['unit'] = line
            
            # Look for prices with currency like "80,00 €"
            elif re.search(r'\d+[,.]?\d*\s*€', line):
                if 'unit_price' not in parsed:
                    parsed['unit_price'] = line
                else:
                    parsed['line_total'] = line
            
            # Look for tax rates like "19%"
            elif re.search(r'\d+%', line):
                parsed['tax_rate'] = line
        
        return parsed
    
    def _group_by_spatial_regions(self, elements: List[Dict]) -> List[List[Dict]]:
        """
        Group text elements into spatial regions using coordinates
        """
        if not elements:
            return []
        
        # Sort elements by Y coordinate (top to bottom)
        sorted_elements = sorted(elements, key=lambda e: e['bbox'][1])
        
        groups = []
        current_group = [sorted_elements[0]]
        
        y_threshold = 20  # pixels - elements within this Y distance are in same region
        
        for element in sorted_elements[1:]:
            current_y = element['bbox'][1]
            last_y = current_group[-1]['bbox'][1]
            
            if abs(current_y - last_y) <= y_threshold:
                # Same region - also check X overlap for columns
                current_group.append(element)
            else:
                # New region
                groups.append(current_group)
                current_group = [element]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _classify_region(self, elements: List[Dict]) -> Tuple[str, float]:
        """
        Classify a spatial region based on content and position
        """
        combined_text = ' '.join([e['text'].lower() for e in elements])
        
        # Check Y position (header typically at top)
        avg_y = np.mean([e['bbox'][1] for e in elements])
        is_top_region = avg_y < 100  # Top 100 pixels
        
        # Check font properties
        has_large_font = any(e.get('size', 12) >= 16 for e in elements)
        has_bold_font = any('bold' in e.get('font', '').lower() for e in elements)
        
        # Classification logic
        if any(keyword in combined_text for keyword in self.header_keywords):
            confidence = 0.9 if (is_top_region and has_large_font) else 0.7
            return 'header', confidence
        
        elif any(keyword in combined_text for keyword in self.vendor_keywords):
            confidence = 0.8 if is_top_region else 0.6
            return 'vendor', confidence
        
        elif any(keyword in combined_text for keyword in self.customer_keywords):
            return 'customer', 0.8
        
        elif any(keyword in combined_text for keyword in self.items_keywords):
            confidence = 0.9 if has_bold_font else 0.7
            return 'line_items_header', confidence
        
        elif any(keyword in combined_text for keyword in self.totals_keywords):
            return 'totals', 0.8
        
        elif any(keyword in combined_text for keyword in self.payment_keywords):
            return 'payment', 0.8
        
        else:
            # Default classification based on position
            if is_top_region:
                return 'header', 0.5
            elif avg_y > 400:  # Bottom region
                return 'footer', 0.5
            else:
                return 'content', 0.3
    
    def _create_chunk(self, elements: List[Dict], chunk_type: str, page_num: int, confidence: float) -> InvoiceChunk:
        """
        Create an InvoiceChunk from grouped elements
        """
        # Combine text content
        content_parts = []
        for element in elements:
            text = element['text'].strip()
            if text:
                content_parts.append(text)
        
        content = ' '.join(content_parts)
        
        # Calculate combined bounding box
        if elements:
            x0 = min(e['bbox'][0] for e in elements)
            y0 = min(e['bbox'][1] for e in elements)
            x1 = max(e['bbox'][2] for e in elements)
            y1 = max(e['bbox'][3] for e in elements)
            bbox = (x0, y0, x1, y1)
        else:
            bbox = (0, 0, 0, 0)
        
        return InvoiceChunk(
            content=content,
            chunk_type=chunk_type,
            elements=elements,
            bbox=bbox,
            page_number=page_num,
            confidence=confidence
        )
    
    def _process_tables(self, tables: List[Dict]) -> List[InvoiceChunk]:
        """
        Convert Camelot table extraction into table chunks
        """
        table_chunks = []
        
        for i, table in enumerate(tables):
            # Convert table data to text
            table_text_lines = []
            for row in table.get('data', []):
                if row:  # Skip empty rows
                    row_text = ' | '.join(str(cell) for cell in row)
                    table_text_lines.append(row_text)
            
            content = '\n'.join(table_text_lines)
            
            # Use table bbox if available
            bbox = table.get('bbox', (0, 0, 0, 0))
            
            chunk = InvoiceChunk(
                content=content,
                chunk_type='table_data',
                elements=[],  # Tables don't have individual elements
                bbox=bbox,
                page_number=table.get('page', 1),
                confidence=table.get('accuracy', 0.8)
            )
            
            table_chunks.append(chunk)
        
        return table_chunks
    
    def _merge_related_chunks(self, chunks: List[InvoiceChunk]) -> List[InvoiceChunk]:
        """
        Merge chunks that belong together (e.g., line_items_header + table_data)
        """
        merged_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # Check if next chunk is related
            if (i + 1 < len(chunks) and 
                self._should_merge_chunks(current_chunk, chunks[i + 1])):
                
                # Merge the chunks
                next_chunk = chunks[i + 1]
                merged_chunk = self._merge_two_chunks(current_chunk, next_chunk)
                merged_chunks.append(merged_chunk)
                i += 2  # Skip next chunk as it's merged
            else:
                merged_chunks.append(current_chunk)
                i += 1
        
        return merged_chunks
    
    def _should_merge_chunks(self, chunk1: InvoiceChunk, chunk2: InvoiceChunk) -> bool:
        """
        Determine if two chunks should be merged
        """
        # Merge line items header with table data
        if (chunk1.chunk_type == 'line_items_header' and 
            chunk2.chunk_type == 'table_data'):
            return True
        
        # Merge chunks on same page that are very close spatially
        if (chunk1.page_number == chunk2.page_number and
            abs(chunk1.bbox[3] - chunk2.bbox[1]) < 30):  # Within 30 pixels
            return True
        
        return False
    
    def _merge_two_chunks(self, chunk1: InvoiceChunk, chunk2: InvoiceChunk) -> InvoiceChunk:
        """
        Merge two chunks into one
        """
        # Combine content
        combined_content = f"{chunk1.content}\n{chunk2.content}"
        
        # Choose the more specific chunk type
        chunk_type = chunk1.chunk_type if chunk1.confidence > chunk2.confidence else chunk2.chunk_type
        if chunk1.chunk_type == 'line_items_header' and chunk2.chunk_type == 'table_data':
            chunk_type = 'line_items'
        
        # Combine bounding boxes
        combined_bbox = (
            min(chunk1.bbox[0], chunk2.bbox[0]),
            min(chunk1.bbox[1], chunk2.bbox[1]),
            max(chunk1.bbox[2], chunk2.bbox[2]),
            max(chunk1.bbox[3], chunk2.bbox[3])
        )
        
        # Combine elements
        combined_elements = chunk1.elements + chunk2.elements
        
        return InvoiceChunk(
            content=combined_content,
            chunk_type=chunk_type,
            elements=combined_elements,
            bbox=combined_bbox,
            page_number=chunk1.page_number,
            confidence=max(chunk1.confidence, chunk2.confidence)
        )
    
    def get_chunk_summary(self, chunks: List[InvoiceChunk]) -> Dict[str, Any]:
        """
        Generate a summary of the chunks
        """
        chunk_types = {}
        total_content_length = 0
        
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            total_content_length += len(chunk.content)
        
        return {
            'total_chunks': len(chunks),
            'chunk_types': chunk_types,
            'average_chunk_size': total_content_length / len(chunks) if chunks else 0,
            'chunks_by_confidence': {
                'high': sum(1 for c in chunks if c.confidence >= 0.8),
                'medium': sum(1 for c in chunks if 0.5 <= c.confidence < 0.8),
                'low': sum(1 for c in chunks if c.confidence < 0.5)
            }
        }
    
    def chunk_invoice_extraction(self, extraction_result: Dict) -> List[InvoiceChunk]:
        """Main method to chunk invoice extraction results"""
        pages = extraction_result.get('text_extraction', {}).get('pages', [])
        tables = extraction_result.get('table_extraction', {}).get('tables', [])
        
        return self.chunk_invoice_spatially(pages, tables)


# Test the chunker
if __name__ == "__main__":
    import sys
    import os
    sys.path.append('..')
    
    from extractor.extractor_pdfplumber import extract_with_pdfplumber_camelot
    
    # Test with your dummy invoice
    pdf_path = "../../invoices/Dummy_Invoice_Styled.pdf"
    if os.path.exists(pdf_path):
        print("🔍 Testing Spatial Invoice Chunker...")
        
        # Extract using your existing method
        extraction_result = extract_with_pdfplumber_camelot(pdf_path)
        
        # Create chunks
        chunker = SpatialInvoiceChunker()
        chunks = chunker.chunk_invoice_extraction(extraction_result)
        
        # Show results
        print(f"\n📊 Created {len(chunks)} intelligent chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i}: {chunk.chunk_type} (confidence: {chunk.confidence:.2f})")
            print(f"Content: {chunk.content[:100]}...")
            print(f"Position: {chunk.bbox}")
        
        # Summary
        summary = chunker.get_chunk_summary(chunks)
        print(f"\n📈 Summary: {summary}")
    else:
        print(f"❌ Test file not found: {pdf_path}")
