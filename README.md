# PDF Pipeline with LangChain Code Improvement

Clean, minimal PDF processing pipeline with LLM-powered code analysis and improvement.

## Current Implementation

**What we have:** Basic but functional LLM-powered code improvement using LangChain chains.

1. **Extract**: Uses pdfplumber + Camelot to extract text and tables from PDFs
2. **Normalize**: Converts raw extraction data into structured invoice metadata  
3. **Analyze**: LangChain LLM chains analyze the normalization code
4. **Improve**: LLM suggests and applies code improvements
5. **Test**: Re-runs pipeline with improved code, shows before/after comparison

## Architecture

```
├── pdf_improvement_demo.py              # Streamlit demo (step-by-step workflow)
├── langchain_code_improvement_agent.py  # LLM chains for code analysis  
├── pdf_pipeline_modular/                # Core PDF processing pipeline
│   ├── extractor/
│   │   └── extractor_pdfplumber.py      # PDF extraction (pdfplumber + Camelot)
│   └── normalizer/
│       └── normalizer.py                # Data normalization (gets improved)
├── invoices/                            # Test data (only dummy invoice tracked)
└── requirements.txt                     # Dependencies
```

## Quick Start

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

## Current Workflow

Step-by-step process with state management (no restart issues):

1. **Upload PDF** → Upload invoice PDF  
2. **Extract Data** → pdfplumber + Camelot extraction
3. **Normalize** → Convert to structured invoice fields
4. **LLM Analysis** → Analyze normalization code with LangChain
5. **Apply & Test** → Apply improvements, show before/after comparison

## Future Roadmap

### Phase 1: Real Agents
- **Tool integration** - Let LLMs execute code, run tests, call APIs
- **ReAct pattern** - Reasoning + Acting loops for autonomous behavior  
- **Error recovery** - Agents that can debug and fix their own mistakes
- **Multi-agent collaboration** - Specialized agents working together

### Phase 2: RAG Implementation  
- **Vector database** - Store PDF extraction patterns, code examples
- **Embedding search** - Find similar invoices/code patterns  
- **Knowledge retrieval** - Pull relevant context for better improvements
- **Learning from history** - Remember successful improvements

### Phase 3: Advanced Features
- **Active learning** - System learns from user feedback
- **Custom model training** - Fine-tune on domain-specific data
- **Multi-document analysis** - Process invoice batches
- **Integration APIs** - Connect to accounting systems

## Current Features

- **Functional pipeline** - PDF → Extract → Normalize → Improve → Test
- **LangChain integration** - Structured LLM chains for code analysis
- **State management** - No restart issues in Streamlit demo
- **Before/after comparison** - Visual results of code improvements  
- **Modular design** - Easy to extend and modify
- **Clean codebase** - Minimal dependencies, well-organized

## Technical Details

**Current LangChain usage:**
- `ChatOpenAI` with GPT-4o-mini
- `LLMChain` with specialized prompts
- `ConversationBufferMemory` for context
- Multiple "personas" (analyzer, improver, validator)

**Dependencies:**
- `streamlit` - Web interface
- `langchain` + `langchain-openai` - LLM orchestration  
- `pdfplumber` + `camelot-py` - PDF processing
- `pandas` - Data handling

## Contributing

This is a learning project exploring the evolution from basic LLM calls → agents → RAG.
Feel free to experiment with the roadmap phases!
