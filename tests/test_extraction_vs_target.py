"""
Focused Tests for PDF Extraction and Chunking
1. Test PDF extraction - check if all fields are being extracted (not necessarily correctly labeled)
2. Test chunking - check if labeling is correct for LLM processing
"""
import sys
import os
import json
sys.path.append('.')
sys.path.append('pdf_pipeline_modular')

from pdf_pipeline_modular.extractor.extractor_pdfplumber import extract_with_pdfplumber_camelot
from pdf_pipeline_modular.chunking.spatial_invoice_chunker import SpatialInvoiceChunker


class ExtractionValidator:
    """Validate PDF extraction and chunking against target data"""
    
    def __init__(self, pdf_path: str, target_file: str):
        self.pdf_path = pdf_path
        self.target_file = target_file
        self.target_data = self._load_target()
        
    def _load_target(self):
        """Load target data from JSON file"""
        with open(self.target_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test_extraction_completeness(self):
        """Test 1: Check if PDF extraction finds all fields (not necessarily correctly labeled)"""
        print("🧪 TEST 1: PDF EXTRACTION COMPLETENESS")
        print("=" * 60)
        print("Testing if extractor finds all required content in the PDF")
        print()
        
        # Extract PDF content
        result = extract_with_pdfplumber_camelot(self.pdf_path)
        
        # Combine all extracted text for searching
        all_text = ""
        for page in result['text_extraction']['pages']:
            for element in page.get('elements', []):
                all_text += " " + element.get('text', '')
        
        # Get table data as text
        table_text = ""
        for table in result['table_extraction']['tables']:
            for row in table['data']:
                table_text += " " + " ".join(str(cell) for cell in row)
        
        combined_text = (all_text + " " + table_text).lower()
        
        # Define what we need to find from target data
        required_fields = self._extract_search_terms()
        
        print(f"🔍 SEARCHING FOR {len(required_fields)} FIELD CATEGORIES:")
        print("-" * 50)
        
        results = {}
        total_found = 0
        total_required = 0
        
        for category, terms in required_fields.items():
            found_terms = []
            missing_terms = []
            
            for term in terms:
                if term.lower() in combined_text:
                    found_terms.append(term)
                else:
                    missing_terms.append(term)
            
            found_count = len(found_terms)
            total_count = len(terms)
            coverage = (found_count / total_count * 100) if total_count > 0 else 0
            
            total_found += found_count
            total_required += total_count
            
            results[category] = {
                'found': found_terms,
                'missing': missing_terms,
                'coverage': coverage,
                'status': '✅' if coverage >= 80 else '⚠️' if coverage >= 50 else '❌'
            }
            
            print(f"{results[category]['status']} {category}: {coverage:.0f}% ({found_count}/{total_count})")
            if found_terms:
                print(f"    Found: {', '.join(found_terms[:3])}{'...' if len(found_terms) > 3 else ''}")
            if missing_terms:
                print(f"    Missing: {', '.join(missing_terms[:3])}{'...' if len(missing_terms) > 3 else ''}")
            print()
        
        overall_coverage = (total_found / total_required * 100) if total_required > 0 else 0
        
        print(f"📊 OVERALL EXTRACTION COVERAGE: {overall_coverage:.1f}% ({total_found}/{total_required})")
        
        return {
            'overall_coverage': overall_coverage,
            'category_results': results,
            'extraction_stats': {
                'pages': len(result['text_extraction']['pages']),
                'text_elements': sum(len(page.get('elements', [])) for page in result['text_extraction']['pages']),
                'tables': len(result['table_extraction']['tables'])
            }
        }
    
    def test_chunking_labeling(self):
        """Test 2: Check if chunking creates correct labels for LLM processing"""
        print("\n🧪 TEST 2: CHUNKING LABELING QUALITY")
        print("=" * 60)
        print("Testing if chunks are correctly labeled for LLM understanding")
        print()
        
        # Extract and chunk
        result = extract_with_pdfplumber_camelot(self.pdf_path)
        chunker = SpatialInvoiceChunker()
        chunks = chunker.chunk_invoice_extraction(result)
        
        print(f"🧩 Created {len(chunks)} chunks")
        print()
        
        # Expected content mapping based on target data
        expected_content = {
            'header': ['rechnung', 'invoice', 'inv-2025-0001', 'example gmbh', 'testkunde'],
            'line_items': ['consulting', 'software', 'development', 'license', 'std', 'stk'],
            'totals': ['zwischensumme', 'umsatzsteuer', 'gesamtbetrag', '1270', '241', '1511'],
            'footer': ['iban', 'bic', 'cobadeff', 'zahlungsziel', 'bank'],
            'customer': ['testkunde', 'alexanderplatz', 'berlin', 'c-1001']
        }
        
        chunk_analysis = []
        labeling_scores = []
        
        for i, chunk in enumerate(chunks):
            print(f"📦 CHUNK {i+1}: {chunk.chunk_type}")
            print("-" * 30)
            
            content_lower = chunk.content.lower()
            
            # Check if chunk type matches content
            correct_indicators = 0
            wrong_indicators = 0
            
            # Count matches for declared type
            declared_type = chunk.chunk_type.lower()
            
            # Find best matching expected type
            best_match_type = None
            best_match_score = 0
            
            for exp_type, keywords in expected_content.items():
                matches = sum(1 for keyword in keywords if keyword in content_lower)
                score = matches / len(keywords) if keywords else 0
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_type = exp_type
                
                if exp_type in declared_type or declared_type in exp_type:
                    correct_indicators = matches
            
            # Calculate labeling accuracy
            label_accuracy = 100 if best_match_type and (best_match_type in declared_type or declared_type in best_match_type) else 0
            content_relevance = best_match_score * 100
            
            overall_score = (label_accuracy + content_relevance) / 2
            labeling_scores.append(overall_score)
            
            status = "✅" if overall_score >= 70 else "⚠️" if overall_score >= 40 else "❌"
            
            chunk_info = {
                'chunk_type': chunk.chunk_type,
                'predicted_type': best_match_type,
                'label_accuracy': label_accuracy,
                'content_relevance': content_relevance,
                'overall_score': overall_score,
                'size': len(chunk.content),
                'confidence': chunk.confidence
            }
            chunk_analysis.append(chunk_info)
            
            print(f"{status} Declared: {chunk.chunk_type}")
            print(f"    Best match: {best_match_type}")
            print(f"    Label accuracy: {label_accuracy:.0f}%")
            print(f"    Content relevance: {content_relevance:.0f}%")
            print(f"    Overall score: {overall_score:.0f}%")
            print(f"    Size: {len(chunk.content)} chars")
            print(f"    Preview: {chunk.content[:80].replace(chr(10), ' ')}...")
            print()
        
        avg_labeling_score = sum(labeling_scores) / len(labeling_scores) if labeling_scores else 0
        
        # Check for essential chunk types
        chunk_types = [chunk.chunk_type.lower() for chunk in chunks]
        essential_types = ['line_items', 'totals']
        missing_essential = [t for t in essential_types if not any(t in ct for ct in chunk_types)]
        
        print(f"📊 CHUNKING LABELING SUMMARY:")
        print("-" * 30)
        print(f"Average labeling accuracy: {avg_labeling_score:.1f}%")
        print(f"Essential chunk types: {len(essential_types) - len(missing_essential)}/{len(essential_types)}")
        if missing_essential:
            print(f"Missing essential types: {', '.join(missing_essential)}")
        
        return {
            'avg_labeling_score': avg_labeling_score,
            'chunk_analysis': chunk_analysis,
            'essential_types_coverage': (len(essential_types) - len(missing_essential)) / len(essential_types) * 100,
            'missing_essential': missing_essential
        }
    
    def _extract_search_terms(self):
        """Extract search terms from target data"""
        terms = {
            'invoice_info': [
                self.target_data['invoice']['number'],
                self.target_data['invoice']['issue_date'].replace('-', '.'),
                self.target_data['invoice']['title']
            ],
            'seller_info': [
                self.target_data['seller']['name'],
                self.target_data['seller']['vat_id'],
                self.target_data['seller']['contact']['email']
            ],
            'buyer_info': [
                self.target_data['buyer']['name'].split()[0],  # "Testkunde"
                self.target_data['buyer']['customer_number'],
                self.target_data['buyer']['address']['city']
            ],
            'line_items': [
                'Consulting', 'Software', 'Development',
                'Std.', 'Stk.', '€'
            ],
            'amounts': [
                str(int(self.target_data['totals']['subtotal_net']['value'])),  # "1270"
                str(self.target_data['totals']['vat_total']['value']).replace('.', ','),  # "241,30"
                str(int(self.target_data['totals']['total_gross']['value']))  # "1511"
            ],
            'payment_info': [
                self.target_data['payment']['bank']['iban'].replace(' ', ''),
                self.target_data['payment']['bank']['bic'],
                self.target_data['payment']['bank']['name']
            ]
        }
        
        return terms
    
    def run_tests(self):
        """Run both extraction and chunking tests"""
        print("🚀 PDF EXTRACTION & CHUNKING VALIDATION")
        print("=" * 70)
        print(f"Source PDF: {self.pdf_path}")
        print(f"Target data: {self.target_file}")
        print()
        
        # Test 1: Extraction completeness
        extraction_results = self.test_extraction_completeness()
        
        # Test 2: Chunking labeling
        chunking_results = self.test_chunking_labeling()
        
        # Overall assessment
        print("\n🎯 FINAL ASSESSMENT")
        print("=" * 40)
        
        extraction_score = extraction_results['overall_coverage']
        chunking_score = chunking_results['avg_labeling_score']
        overall_score = (extraction_score + chunking_score) / 2
        
        def grade(score):
            if score >= 85: return "A+", "🟢"
            elif score >= 75: return "A", "✅"
            elif score >= 65: return "B", "🟡"
            elif score >= 50: return "C", "⚠️"
            else: return "F", "❌"
        
        ext_grade, ext_icon = grade(extraction_score)
        chunk_grade, chunk_icon = grade(chunking_score)
        overall_grade, overall_icon = grade(overall_score)
        
        print(f"{ext_icon} Extraction Coverage: {extraction_score:.1f}% (Grade: {ext_grade})")
        print(f"{chunk_icon} Chunking Labeling: {chunking_score:.1f}% (Grade: {chunk_grade})")
        print(f"{overall_icon} Overall Pipeline: {overall_score:.1f}% (Grade: {overall_grade})")
        
        return {
            'extraction': extraction_results,
            'chunking': chunking_results,
            'final_scores': {
                'extraction': extraction_score,
                'chunking': chunking_score,
                'overall': overall_score
            }
        }


def main():
    pdf_path = "invoices/Dummy_Invoice_Styled.pdf"
    target_file = "tests/target.json"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    if not os.path.exists(target_file):
        print(f"❌ Target file not found: {target_file}")
        return
    
    validator = ExtractionValidator(pdf_path, target_file)
    results = validator.run_tests()
    
    # Save results
    with open('validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Detailed results saved to validation_results.json")


if __name__ == "__main__":
    main()
