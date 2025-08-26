PDF → Extract text/tables → Smart chunking → LLM-ready structure

## Logic

**1. PDF extraction**: Two-step process - pdfplumber for text, then camelot for tables e.g.:
```python
# Step 1: pdfplumber extracts individual words with coordinates
{'text': 'Software License', 'bbox': [150, 400, 250, 415], 'font': 'Arial'}
{'text': '1,00', 'bbox': [300, 400, 330, 415], 'font': 'Arial'}
{'text': '120,00 €', 'bbox': [450, 400, 500, 415], 'font': 'Arial'}

# Step 2: camelot detects and extracts tables separately
[['Description', 'Qty', 'Price'], ['Software License', '1,00', '120,00 €']]
```
*Problem*: Text fragments scattered by coordinates + separate table arrays - no logical connection between them.

**2. chunking**: reconstruct logical meaning from spatial fragments using coordinates and patterns e.g.: 
```
TABLE: Invoice Line Items
==================================================
LINE ITEM 1:
  Description: Consulting Services – July 2025
  Quantity: 10,00
  Unit: Std.
  Unit Price: 80,00 €
  Tax Rate: 19%
  Line Total: 800,00 €
------------------------------
LINE ITEM 2:
  Description: Software License – Pro Plan (1 Monat)
  Quantity: 1,00
  Unit: Stk.
  Unit Price: 120,00 €
  Tax Rate: 19%
  Line Total: 120,00 €
```
*Solution*: Group by Y-coordinates + content patterns to create semantic structure that LLMs can parse.

## Testing

**Pipeline validation**: Validates extraction completeness and chunking quality against ground truth data.

```bash
python tests/test_extraction_vs_target.py
```

**Test 1 - Extraction Coverage**: Checks if all required fields from PDF are found (invoice numbers, amounts, dates, etc.)  
**Test 2 - Chunking Labeling**: Validates chunks are correctly labeled for LLM processing (line_items, totals, etc.)

Results saved to `tests/results/` with detailed breakdowns and accuracy scores.

