# PDF Pipeline with LangChain Code Improvement

Clean, minimal solution for PDF processing with intelligent code improvement using LangChain agents.

## What This Does

1. **Extract**: Uses pdfplumber + Camelot to extract text and tables from PDFs
2. **Normalize**: Converts raw extraction data into structured invoice metadata
3. **Analyze**: LangChain agent analyzes the normalization code for improvements
4. **Improve**: Agent suggests and applies code improvements
5. **Test**: Immediately re-runs pipeline with improved code and shows before/after comparison

## Files Structure

```
clean_solution/
├── pdf_improvement_demo.py          # Main Streamlit demo (NO RESTART ISSUES!)
├── langchain_code_improvement_agent.py  # LangChain agent for code analysis
├── pdf_pipeline_modular/            # Core PDF processing pipeline
│   ├── extractor/
│   │   └── extractor_pdfplumber.py  # PDF extraction with pdfplumber + Camelot
│   └── normalizer/
│       └── normalizer.py            # Data normalization (gets improved by agent)
├── invoices/                        # Test PDF files
│   └── Dummy_Invoice_Styled.pdf
└── requirements.txt                 # Dependencies
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Run the demo:**
   ```bash
   streamlit run pdf_improvement_demo.py
   ```

## How It Works

The demo is a **step-by-step process** that maintains state between steps (no restarts!):

1. **Upload PDF** → Upload any invoice PDF
2. **Extract Data** → Extracts text and tables using pdfplumber + Camelot
3. **Normalize** → Converts raw data to structured invoice fields
4. **Agent Analysis** → LangChain agent analyzes the normalization code
5. **Apply & Test** → Applies improvements and shows before/after comparison

## Key Features

- ✅ **No restart issues** - Uses proper Streamlit session state management
- ✅ **Real-time improvement testing** - Immediately shows results of code improvements
- ✅ **Clean step-by-step workflow** - Easy to follow and debug
- ✅ **Before/after comparison** - Visual comparison of extraction results
- ✅ **Minimal dependencies** - Only essential packages
- ✅ **Modular design** - Easy to extend and modify

## Dependencies

- `streamlit` - Web interface
- `langchain` - AI agent framework
- `openai` - LLM API
- `pdfplumber` - PDF text extraction
- `camelot-py` - Table extraction
- `pandas` - Data handling

## Notes

- The LangChain agent analyzes the `normalizer.py` file and suggests improvements
- Improvements are applied directly to the code and tested immediately
- Results are saved to JSON files with timestamps
- The original normalizer is backed up before applying changes
