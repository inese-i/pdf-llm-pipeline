"""
PDF Pipeline with LangChain Code Improvement Demo
Clean, minimal solution that works without restarts.
"""

import streamlit as st
import os
import sys
import json
import importlib
from datetime import datetime

# Add paths
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.join(os.getcwd(), 'pdf_pipeline_modular'))

# Import core components
from pdf_pipeline_modular.extractor.extractor_pdfplumber import extract_with_pdfplumber_camelot
from pdf_pipeline_modular.normalizer.normalizer import format_llm_ready

# Import LangChain agent
try:
    from langchain_code_improvement_agent import LangChainCodeImprovementAgent
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    st.sidebar.error(f"❌ LangChain agents not available: {e}")

# Page config
st.set_page_config(
    page_title="PDF Pipeline Improvement Demo",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 PDF Pipeline with LangChain Code Improvement")
st.markdown("Clean solution: Extract → Normalize → Analyze → Improve → Test")

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

# Sidebar progress
st.sidebar.title("🎯 Progress")
steps = [
    "1️⃣ Upload PDF",
    "2️⃣ Extract Data", 
    "3️⃣ Normalize",
    "4️⃣ Agent Analysis",
    "5️⃣ Apply & Test"
]

for i, step in enumerate(steps, 1):
    if st.session_state.current_step > i:
        st.sidebar.success(step)
    elif st.session_state.current_step == i:
        st.sidebar.info(step + " ← Current")
    else:
        st.sidebar.text(step)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    # Step 1: File Upload
    if st.session_state.current_step == 1:
        st.header("1️⃣ Upload PDF File")
        
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file is not None:
            # Save file
            pdf_path = f"temp_{uploaded_file.name}"
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.session_state.data['pdf_path'] = pdf_path
            st.session_state.data['pdf_name'] = uploaded_file.name
            
            st.success(f"✅ Uploaded: {uploaded_file.name}")
            
            if st.button("📄 Start Extraction", type="primary"):
                st.session_state.current_step = 2
                st.rerun()

    # Step 2: Extraction
    elif st.session_state.current_step == 2:
        st.header("2️⃣ PDF Extraction")
        
        pdf_path = st.session_state.data['pdf_path']
        st.info(f"Processing: {st.session_state.data['pdf_name']}")
        
        if 'extraction_done' not in st.session_state.data:
            if st.button("🔍 Extract PDF Content"):
                with st.spinner("Extracting PDF content..."):
                    try:
                        result = extract_with_pdfplumber_camelot(pdf_path)
                        pages = result['text_extraction']['pages']
                        tables = result['table_extraction']['tables']
                        
                        # Process tables
                        table_rows = []
                        for table in tables:
                            if 'data' in table:
                                table_rows.extend(table['data'])
                        
                        # Store results
                        st.session_state.data['extraction_result'] = result
                        st.session_state.data['pages'] = pages
                        st.session_state.data['table_rows'] = table_rows
                        st.session_state.data['extraction_done'] = True
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Extraction failed: {e}")
        else:
            # Show extraction results
            pages = st.session_state.data['pages']
            table_rows = st.session_state.data['table_rows']
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Pages Extracted", len(pages))
                st.metric("Text Elements", sum(len(p.get('elements', [])) for p in pages))
            with col_b:
                st.metric("Tables Found", len(st.session_state.data['extraction_result']['table_extraction']['tables']))
                st.metric("Table Rows", len(table_rows))
            
            st.success("✅ Extraction completed")
            
            if st.button("➡️ Continue to Normalization", type="primary"):
                st.session_state.current_step = 3
                st.rerun()

    # Step 3: Normalization
    elif st.session_state.current_step == 3:
        st.header("3️⃣ Data Normalization")
        
        if 'normalization_done' not in st.session_state.data:
            if st.button("🔧 Normalize Data"):
                with st.spinner("Normalizing data..."):
                    try:
                        pages = st.session_state.data['pages']
                        table_rows = st.session_state.data['table_rows']
                        
                        normalized_data = format_llm_ready(pages, table_rows)
                        
                        st.session_state.data['original_normalized'] = normalized_data
                        st.session_state.data['normalization_done'] = True
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Normalization failed: {e}")
        else:
            # Show normalization results
            data = st.session_state.data['original_normalized']
            
            if 'invoice_metadata' in data:
                metadata = data['invoice_metadata']
                found_fields = sum(1 for v in metadata.values() if v)
                total_fields = len(metadata)
                
                st.metric("Invoice Fields Extracted", f"{found_fields}/{total_fields}")
                
                # Show extracted fields
                st.subheader("📋 Extracted Invoice Data")
                for key, value in metadata.items():
                    if value:
                        st.success(f"✅ {key.replace('_', ' ').title()}: {value}")
                    else:
                        st.warning(f"❌ {key.replace('_', ' ').title()}: Not found")
            
            st.success("✅ Normalization completed")
            
            if AGENTS_AVAILABLE:
                if st.button("🤖 Run Agent Analysis", type="primary"):
                    st.session_state.current_step = 4
                    st.rerun()
            else:
                st.warning("🤖 LangChain agents not available - cannot proceed to analysis")

    # Step 4: Agent Analysis
    elif st.session_state.current_step == 4 and AGENTS_AVAILABLE:
        st.header("4️⃣ LangChain Agent Analysis")
        
        if 'agent_analysis_done' not in st.session_state.data:
            if st.button("🔍 Analyze Code Quality"):
                with st.spinner("Running LangChain agent analysis..."):
                    try:
                        agent = LangChainCodeImprovementAgent()
                        
                        # Prepare input
                        pages = st.session_state.data['pages']
                        table_rows = st.session_state.data['table_rows']
                        normalized_data = st.session_state.data['original_normalized']
                        
                        agent_input = {
                            "extraction_stats": {
                                "pages": len(pages),
                                "total_elements": sum(len(p.get("elements", [])) for p in pages),
                                "tables": len(table_rows)
                            },
                            "normalized_data": normalized_data,
                            "raw_pages": pages,
                            "raw_tables": table_rows
                        }
                        
                        # Run analysis
                        analysis = agent.analyze_code_quality(agent_input, "pdf_pipeline_modular/normalizer/normalizer.py")
                        
                        # Get improvements
                        target_function = agent._extract_function_code("format_llm_ready", "pdf_pipeline_modular/normalizer/normalizer.py")
                        
                        if target_function:
                            improvements = agent.improve_function(analysis, target_function)
                            validation = agent.validate_improvement(target_function, improvements, json.dumps(normalized_data))
                        else:
                            improvements = "No target function found"
                            validation = "Cannot validate without target function"
                        
                        # Store results
                        st.session_state.data['agent'] = agent
                        st.session_state.data['analysis'] = analysis
                        st.session_state.data['improvements'] = improvements
                        st.session_state.data['validation'] = validation
                        st.session_state.data['agent_analysis_done'] = True
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Agent analysis failed: {e}")
        else:
            # Show analysis results
            st.subheader("🔍 Code Analysis")
            st.text_area("Analysis Report", st.session_state.data['analysis'], height=150)
            
            st.subheader("💡 Suggested Improvements")
            with st.expander("View Code Improvements"):
                st.code(st.session_state.data['improvements'], language="python")
            
            st.subheader("✅ Validation")
            st.text_area("Validation Report", st.session_state.data['validation'], height=100)
            
            if st.button("🚀 Apply & Test Improvements", type="primary"):
                st.session_state.current_step = 5
                st.rerun()

    # Step 5: Apply & Test
    elif st.session_state.current_step == 5:
        st.header("5️⃣ Apply & Test Improvements")
        
        if 'improvements_applied' not in st.session_state.data:
            with st.spinner("Applying improvements and testing..."):
                try:
                    agent = st.session_state.data['agent']
                    improvements = st.session_state.data['improvements']
                    
                    # Apply improvements
                    success = agent.apply_improvements_to_normalizer(improvements, "pdf_pipeline_modular/normalizer/normalizer.py")
                    
                    if success:
                        st.success("✅ Improvements applied successfully!")
                        
                        # Reload normalizer module
                        if 'pdf_pipeline_modular.normalizer.normalizer' in sys.modules:
                            importlib.reload(sys.modules['pdf_pipeline_modular.normalizer.normalizer'])
                        
                        from pdf_pipeline_modular.normalizer.normalizer import format_llm_ready as improved_normalizer
                        
                        # Re-run normalization with improvements
                        pages = st.session_state.data['pages']
                        table_rows = st.session_state.data['table_rows']
                        improved_data = improved_normalizer(pages, table_rows)
                        
                        st.session_state.data['improved_normalized'] = improved_data
                        st.session_state.data['improvements_applied'] = True
                        
                        st.rerun()
                    else:
                        st.error("❌ Failed to apply improvements")
                        
                except Exception as e:
                    st.error(f"❌ Error applying improvements: {e}")
        else:
            # Show before/after comparison
            st.subheader("📊 Before vs After Comparison")
            
            original_data = st.session_state.data['original_normalized']
            improved_data = st.session_state.data['improved_normalized']
            
            col_before, col_after = st.columns(2)
            
            with col_before:
                st.markdown("#### 🔻 BEFORE (Original)")
                if 'invoice_metadata' in original_data:
                    metadata = original_data['invoice_metadata']
                    found = sum(1 for v in metadata.values() if v)
                    st.metric("Fields Found", f"{found}/{len(metadata)}")
                    
                    for key, value in metadata.items():
                        if value:
                            st.success(f"✅ {key}: {value}")
                        else:
                            st.error(f"❌ {key}: Not found")
            
            with col_after:
                st.markdown("#### 🔺 AFTER (Improved)")
                if 'invoice_metadata' in improved_data:
                    metadata = improved_data['invoice_metadata']
                    found = sum(1 for v in metadata.values() if v)
                    st.metric("Fields Found", f"{found}/{len(metadata)}")
                    
                    for key, value in metadata.items():
                        if value:
                            st.success(f"✅ {key}: {value}")
                        else:
                            st.error(f"❌ {key}: Not found")
            
            # Calculate improvement
            original_found = sum(1 for v in original_data.get('invoice_metadata', {}).values() if v)
            improved_found = sum(1 for v in improved_data.get('invoice_metadata', {}).values() if v)
            improvement = improved_found - original_found
            
            if improvement > 0:
                st.success(f"🎯 **IMPROVEMENT: +{improvement} additional fields extracted!**")
            elif improvement == 0:
                st.info("📊 Same extraction level maintained (code structure improved)")
            else:
                st.warning(f"⚠️ {abs(improvement)} fewer fields (may need adjustment)")
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results = {
                "timestamp": timestamp,
                "original_fields": original_found,
                "improved_fields": improved_found,
                "improvement": improvement,
                "analysis": st.session_state.data['analysis'],
                "improvements": st.session_state.data['improvements']
            }
            
            results_file = f"improvement_results_{timestamp}.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            st.info(f"📁 Results saved to: {results_file}")

with col2:
    st.subheader("📋 Session Data")
    if st.session_state.data:
        st.json({k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                for k, v in st.session_state.data.items() 
                if k not in ['pages', 'table_rows', 'extraction_result', 'agent']})

# Reset button
if st.button("🔄 Start Over"):
    st.session_state.clear()
    st.rerun()
