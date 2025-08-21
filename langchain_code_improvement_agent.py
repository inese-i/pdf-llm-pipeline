#!/usr/bin/env python3
"""
LangChain Code Improvement Agent
Multi-agent system for intelligent code analysis and improvement using LangChain
Integrates with existing PDF pipeline for analysis while leveraging LangChain's strengths
"""

import os
import sys
import json
import importlib.util
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the pipeline module to path
sys.path.append('pdf_pipeline_modular')

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

class LangChainCodeImprovementAgent:
    """
    Multi-agent system using LangChain for intelligent code analysis and improvement
    Integrates with existing PDF extraction pipeline
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the multi-agent LangChain system"""
        
        # Setup OpenAI API
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=self.api_key
        )
        
        # Conversation memory for agent context
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create specialized agents
        self.code_analyzer_agent = self._create_code_analyzer_agent()
        self.improvement_generator_agent = self._create_improvement_generator_agent()
        self.validation_agent = self._create_validation_agent()
        
        print("🤖 LangChain Code Improvement Agents initialized")
        print("📋 Using your existing PDF extraction pipeline")
    
    def _create_code_analyzer_agent(self):
        """Create specialized code analysis agent"""
        analysis_prompt = PromptTemplate(
            input_variables=["extraction_data", "code_content"],
            template="""
You are a specialized CODE ANALYSIS AGENT with expertise in PDF extraction and data normalization.

EXTRACTION RESULTS TO ANALYZE:
{extraction_data}

CURRENT CODE TO ANALYZE:
{code_content}

Your task is to analyze the current code and extraction results to identify:
1. Missing fields that should be extracted from invoices/documents
2. Inefficient extraction patterns or logic
3. Code quality issues (error handling, structure, etc.)
4. Opportunities for improvement in data normalization

Focus on practical improvements that will enhance the PDF extraction pipeline.
Provide a detailed analysis with specific recommendations.
"""
        )
        
        return LLMChain(llm=self.llm, prompt=analysis_prompt)
    
    def _create_improvement_generator_agent(self):
        """Create specialized improvement generation agent"""
        improvement_prompt = PromptTemplate(
            input_variables=["analysis", "target_function"],
            template="""
You are a specialized CODE IMPROVEMENT AGENT that generates enhanced code based on analysis.

ANALYSIS FROM CODE ANALYZER:
{analysis}

TARGET FUNCTION TO IMPROVE:
{target_function}

Your task is to generate IMPROVED CODE that addresses the issues identified in the analysis.

Requirements:
1. Maintain the same function signature and interface
2. Add comprehensive regex patterns for better field extraction
3. Improve error handling and edge cases
4. Add clear comments explaining improvements
5. Ensure the code is production-ready and well-structured

Provide the improved code with explanations of what was enhanced.
"""
        )
        
        return LLMChain(llm=self.llm, prompt=improvement_prompt)
    
    def _create_validation_agent(self):
        """Create specialized validation agent"""
        validation_prompt = PromptTemplate(
            input_variables=["original_code", "improved_code", "test_data"],
            template="""
You are a specialized VALIDATION AGENT that reviews code improvements for correctness and compatibility.

ORIGINAL CODE:
{original_code}

IMPROVED CODE:
{improved_code}

TEST DATA:
{test_data}

Your task is to validate the improved code by:
1. Checking interface compatibility (same inputs/outputs)
2. Verifying the improvements address real issues
3. Identifying potential bugs or issues
4. Suggesting test cases to validate the improvements
5. Confirming the code follows best practices

Provide a comprehensive validation report with any concerns or recommendations.
"""
        )
        
        return LLMChain(llm=self.llm, prompt=validation_prompt)
    
    def extract_and_analyze(self, pdf_path: str) -> Dict[str, Any]:
        """Extract PDF using existing pipeline and prepare for analysis"""
        print(f"📄 Extracting PDF using your existing pipeline: {pdf_path}")
        
        try:
            # Import and use existing extraction pipeline
            from extractor.extractor_pdfplumber import extract_with_pdfplumber_camelot
            from normalizer.normalizer import format_llm_ready
            
            # Extract PDF
            extraction_result = extract_with_pdfplumber_camelot(pdf_path)
            pages = extraction_result['text_extraction']['pages']
            tables = extraction_result['table_extraction']['tables']
            
            # Convert tables to expected format
            table_rows = []
            for table in tables:
                if 'data' in table:
                    table_rows.extend(table['data'])
            
            # Apply normalization
            normalized_data = format_llm_ready(pages, table_rows)
            
            return {
                "extraction_stats": {
                    "pages": len(pages),
                    "total_elements": sum(len(page.get("elements", [])) for page in pages),
                    "tables": len(tables),
                    "table_rows": len(table_rows)
                },
                "normalized_data": normalized_data,
                "raw_pages": pages,
                "raw_tables": table_rows
            }
            
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}
    
    def analyze_code_quality(self, extraction_results: Dict[str, Any], code_file_path: str) -> str:
        """Analyze code quality using LangChain agent"""
        print("🔍 Analyzing code quality with LangChain agent...")
        
        # Read the code file
        try:
            with open(code_file_path, 'r') as f:
                code_content = f.read()
        except Exception as e:
            return f"Error reading code file: {str(e)}"
        
        # Use code analyzer agent
        analysis_result = self.code_analyzer_agent.run(
            extraction_data=json.dumps(extraction_results["extraction_stats"]),
            code_content=code_content[:2000]  # Limit content for analysis
        )
        
        return analysis_result
    
    def improve_function(self, analysis: str, target_function: str) -> str:
        """Generate improvements using LangChain agent"""
        print("🛠️ Generating code improvements...")
        
        improvements = self.improvement_generator_agent.run(
            analysis=analysis,
            target_function=target_function
        )
        
        return improvements
    
    def validate_improvement(self, original_code: str, improved_code: str, test_data: str) -> str:
        """Validate improvements using LangChain agent"""
        print("✅ Validating improvements...")
        
        validation = self.validation_agent.run(
            original_code=original_code[:1000],  # Limit for context
            improved_code=improved_code[:1000],
            test_data=test_data[:500]
        )
        
        return validation
    
    def apply_improvements_to_normalizer(self, improvements: str, normalizer_path: str) -> bool:
        """Apply LangChain agent improvements directly to the normalizer file"""
        print("🔧 Applying improvements directly to normalizer file...")
        
        try:
            # Create backup
            backup_path = f"{normalizer_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(normalizer_path, 'r') as f:
                original_content = f.read()
            
            with open(backup_path, 'w') as f:
                f.write(original_content)
            print(f"📁 Backup created: {backup_path}")
            
            # Extract code from improvements (look for Python code blocks)
            import re
            code_blocks = re.findall(r'```python\n(.*?)\n```', improvements, re.DOTALL)
            
            if code_blocks:
                # Get the largest code block (likely the main improvement)
                main_improvement = max(code_blocks, key=len)
                
                # Add timestamp and append to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                improvement_header = f"\n\n# LANGCHAIN AGENT IMPROVEMENTS - {timestamp}\n\n"
                
                with open(normalizer_path, 'a') as f:
                    f.write(improvement_header)
                    f.write(main_improvement)
                
                print(f"✅ Applied {len(main_improvement)} characters of improved code")
                return True
            else:
                print("❌ No code blocks found in improvements")
                return False
                
        except Exception as e:
            print(f"❌ Error applying improvements: {e}")
            return False

    def run_full_improvement_cycle(self, pdf_path: str, target_function: Optional[str] = None) -> Dict[str, Any]:
        """Run complete improvement cycle with agent collaboration and direct application"""
        print("🚀 LANGCHAIN AGENT-BASED CODE IMPROVEMENT")
        print("=" * 60)
        
        results = {"timestamp": datetime.now().isoformat()}
        
        # Step 1: Extract PDF using existing pipeline
        extraction_results = self.extract_and_analyze(pdf_path)
        if "error" in extraction_results:
            return {"error": extraction_results["error"]}
        
        results["extraction"] = extraction_results["extraction_stats"]
        
        # Step 2: Analyze code quality with LangChain
        normalizer_path = "pdf_pipeline_modular/normalizer/normalizer.py"
        analysis = self.analyze_code_quality(extraction_results, normalizer_path)
        results["analysis"] = analysis
        
        print("📊 Analysis complete:")
        print(analysis[:300] + "..." if len(analysis) > 300 else analysis)
        
        # Step 3: Target specific function for improvement
        if not target_function:
            # Default to format_llm_ready function
            target_function = self._extract_function_code("format_llm_ready", normalizer_path)
        
        if target_function:
            # Step 4: Generate improvements
            improvements = self.improve_function(analysis, target_function)
            results["improvements"] = improvements
            
            print("🛠️ Improvements generated:")
            print(improvements[:300] + "..." if len(improvements) > 300 else improvements)
            
            # Step 5: Apply improvements directly to normalizer file
            success = self.apply_improvements_to_normalizer(improvements, normalizer_path)
            results["applied"] = "Success" if success else "Failed"
            
            if success:
                print("✅ Improvements applied directly to normalizer.py")
            else:
                print("❌ Failed to apply improvements")
            
            # Step 6: Validate improvements
            validation = self.validate_improvement(
                target_function, 
                improvements, 
                json.dumps(extraction_results["normalized_data"])
            )
            results["validation"] = validation
            
            print("✅ Validation complete:")
            print(validation[:300] + "..." if len(validation) > 300 else validation)
        else:
            results["error"] = "Could not extract target function code"
        
        # Save results
        results_file = f"langchain_agent_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("🎉 AGENT-BASED IMPROVEMENT CYCLE COMPLETE!")
        extraction_data = results.get('extraction', {})
        if isinstance(extraction_data, dict):
            print(f"📊 Extracted {extraction_data.get('total_elements', 0)} elements from {extraction_data.get('pages', 0)} pages")
        else:
            print("📊 PDF extraction completed")
        print("🔍 Analysis and improvements generated by LangChain agents")
        if results.get("applied") == "Success":
            print("✅ Improvements applied directly to normalizer.py")
        else:
            print("❌ Failed to apply improvements to normalizer.py")
        print(f"📁 Results saved to: {results_file}")
        return results
    
    def _extract_function_code(self, function_name: str, file_path: str) -> Optional[str]:
        """Extract specific function code from file"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            function_lines = []
            in_function = False
            indent_level = 0
            
            for line in lines:
                if f"def {function_name}(" in line:
                    in_function = True
                    indent_level = len(line) - len(line.lstrip())
                    function_lines.append(line)
                elif in_function:
                    current_indent = len(line) - len(line.lstrip())
                    if line.strip() and current_indent <= indent_level and not line.strip().startswith('#'):
                        break
                    function_lines.append(line)
            
            return ''.join(function_lines) if function_lines else None
            
        except Exception as e:
            print(f"Error extracting function {function_name}: {e}")
            return None


def main():
    """Main execution function"""
    
    # Initialize the LangChain agent system
    agent = LangChainCodeImprovementAgent()
    
    # Run the full improvement cycle
    results = agent.run_full_improvement_cycle("invoices/Dummy_Invoice_Styled.pdf")
    
    if "error" not in results:
        print("🎉 AGENT-BASED IMPROVEMENT CYCLE COMPLETE!")
        print(f"📊 Extracted {results.get('extraction', {}).get('total_elements', 0)} elements from {results.get('extraction', {}).get('pages', 0)} pages")
        print("🔍 Analysis and improvements generated by LangChain agents")
        print("✅ Results saved with validation feedback")


if __name__ == "__main__":
    main()