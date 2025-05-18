# quotation_graph_builder.py
import os
import json
import re # Import regular expressions
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from llm_providers import get_llm_instance
from llm_prompts import (
    VENDOR_REPLY_PARSING_PROMPT_TEMPLATE_STRING,
    QUOTATION_STRUCTURE_JSON_PROMPT_TEMPLATE_STRING
)
from pdf_utils import create_pdf_quotation_bytes
from fpdf import FPDF

# ... (create_error_pdf_instance and sanitize_for_standard_font remain the same) ...
def create_error_pdf_instance():
    pdf = FPDF()
    pdf.add_page()
    font_regular_path = os.path.join('assets', 'fonts', 'DejaVuSansCondensed.ttf')
    font_bold_path = os.path.join('assets', 'fonts', 'DejaVuSansCondensed-Bold.ttf')
    dejavu_loaded = False
    try:
        if os.path.exists(font_regular_path) and os.path.exists(font_bold_path):
            pdf.add_font('DejaVu', '', font_regular_path, uni=True)
            pdf.add_font('DejaVu', 'B', font_bold_path, uni=True)
            pdf.set_font("DejaVu", "B", 12)
            dejavu_loaded = True
        else:
            print("QuotationGraphBuilder: DejaVu fonts not found for error PDF. Using Helvetica.")
            pdf.set_font("Helvetica", "B", 12)
    except Exception as e:
        print(f"QuotationGraphBuilder: Error loading DejaVu for error PDF: {e}. Using Helvetica.")
        pdf.set_font("Helvetica", "B", 12)
    return pdf, dejavu_loaded

def sanitize_for_standard_font(text_string: str) -> str:
    if not isinstance(text_string, str):
        text_string = str(text_string)
    return text_string.encode('latin-1', 'replace').decode('latin-1')


class QuotationGenerationState(TypedDict):
    enquiry_details: dict
    vendor_reply_text: str
    parsed_vendor_info_text: str
    structured_quotation_data: Dict[str, Any]
    pdf_output_bytes: bytes
    ai_provider: str

def fetch_data_node(state: QuotationGenerationState):
    return {
        "enquiry_details": state["enquiry_details"],
        "vendor_reply_text": state["vendor_reply_text"],
        "ai_provider": state["ai_provider"]
    }

def parse_vendor_reply_node(state: QuotationGenerationState):
    vendor_reply = state["vendor_reply_text"]
    enquiry_details = state["enquiry_details"]
    provider = state["ai_provider"]
    try:
        llm = get_llm_instance(provider)
        prompt = ChatPromptTemplate.from_template(VENDOR_REPLY_PARSING_PROMPT_TEMPLATE_STRING)
        parser = StrOutputParser()
        chain = prompt | llm | parser
        parsed_info_str = chain.invoke({
            "vendor_reply": vendor_reply,
            "destination": enquiry_details.get("destination"),
            "num_days": enquiry_details.get("num_days")
        })
        return {"parsed_vendor_info_text": parsed_info_str}
    except Exception as e:
        print(f"Error parsing vendor reply with LLM ({provider}): {e}")
        return {"parsed_vendor_info_text": f"Error parsing vendor reply using {provider}. Detail: {str(e)}"}


def structure_data_for_pdf_node(state: QuotationGenerationState):
    enquiry = state["enquiry_details"]
    vendor_parsed_text = state["parsed_vendor_info_text"]
    provider = state["ai_provider"]

    try:
        llm = get_llm_instance(provider)
        num_days_int = int(enquiry.get("num_days", 0))
        num_nights = num_days_int - 1 if num_days_int > 0 else 0

        json_prompt_str = QUOTATION_STRUCTURE_JSON_PROMPT_TEMPLATE_STRING
        
        if provider == "OpenRouter" and ("gpt" in os.getenv("OPENROUTER_DEFAULT_MODEL", "").lower() or \
                                         "claude-3" in os.getenv("OPENROUTER_DEFAULT_MODEL", "").lower()):
            llm_for_json = get_llm_instance(provider) 
            if not hasattr(llm_for_json, 'model_kwargs') or llm_for_json.model_kwargs is None:
                llm_for_json.model_kwargs = {}
            llm_for_json.model_kwargs["response_format"] = {"type": "json_object"}
            prompt = ChatPromptTemplate.from_template(json_prompt_str)
            chain = prompt | llm_for_json | JsonOutputParser()
        elif provider == "Gemini":
            updated_json_prompt_str = json_prompt_str.replace("```json", "Please provide your response strictly in the following JSON format, ensuring all strings are correctly escaped:\n```json")
            prompt = ChatPromptTemplate.from_template(updated_json_prompt_str)
            chain = prompt | llm | StrOutputParser() 
        else: 
            prompt = ChatPromptTemplate.from_template(json_prompt_str)
            chain = prompt | llm | StrOutputParser()

        response_data = chain.invoke({
            "destination": enquiry.get("destination", "N/A"),
            "num_days": str(enquiry.get("num_days", "N/A")),
            "num_nights": str(num_nights),
            "traveler_count": str(enquiry.get("traveler_count", "N/A")),
            "trip_type": enquiry.get("trip_type", "N/A"),
            "client_name_placeholder": f"Mr./Ms. {enquiry.get('client_name_actual', 'Valued Client')}",
            "vendor_parsed_text": vendor_parsed_text
        })

        structured_data = {}
        raw_llm_output_for_error = "" 

        if isinstance(response_data, str):
            raw_llm_output_for_error = response_data 
            try:
                # --- START: MORE ROBUST JSON EXTRACTION ---
                # 1. Try to find JSON within ```json ... ``` markdown
                match = re.search(r"```json\s*(\{.*?\})\s*```", response_data, re.DOTALL)
                if match:
                    potential_json_str = match.group(1)
                else:
                    # 2. Fallback: find the first '{' and last '}'
                    cleaned_response = response_data.strip()
                    json_start_index = cleaned_response.find('{')
                    if json_start_index == -1:
                        raise json.JSONDecodeError("No JSON object found in the response.", cleaned_response, 0)
                    
                    # To find the matching '}', we need to count braces
                    open_braces = 0
                    json_end_index = -1
                    for i in range(json_start_index, len(cleaned_response)):
                        if cleaned_response[i] == '{':
                            open_braces += 1
                        elif cleaned_response[i] == '}':
                            open_braces -= 1
                            if open_braces == 0:
                                json_end_index = i
                                break
                    
                    if json_end_index == -1:
                        raise json.JSONDecodeError("Incomplete JSON object (no matching '}') in the response.", cleaned_response, 0)
                    
                    potential_json_str = cleaned_response[json_start_index : json_end_index + 1]
                
                structured_data = json.loads(potential_json_str)
                # --- END: MORE ROBUST JSON EXTRACTION ---

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON from LLM. Error: {e}. Preview: '{raw_llm_output_for_error[:200]}...'"
                print(error_msg) # Log the specific JSON error and a preview
                # print(f"LLM String Output was:\n{raw_llm_output_for_error}") # Full output can be very long
                return {"structured_quotation_data": {"error": "Failed to parse JSON from LLM", "raw_output": raw_llm_output_for_error}}
        elif isinstance(response_data, dict): 
            structured_data = response_data
            raw_llm_output_for_error = json.dumps(response_data, indent=2)
        else:
            return {"structured_quotation_data": {"error": "Unexpected LLM output type for JSON.", "raw_output": str(response_data)}}

        # Data sanitization (ensure list items are strings for PDF generation robustness)
        for key_list in ["inclusions", "exclusions", "standard_exclusions_list", "important_notes"]:
            if key_list in structured_data and isinstance(structured_data[key_list], list):
                structured_data[key_list] = [str(item) for item in structured_data[key_list]]
        
        if "detailed_itinerary" in structured_data and isinstance(structured_data["detailed_itinerary"], list):
            for item in structured_data["detailed_itinerary"]:
                if isinstance(item, dict):
                    for k,v in item.items(): item[k] = str(v) # Convert all itinerary values to strings
        
        if "hotel_details" in structured_data and isinstance(structured_data["hotel_details"], list):
            for item in structured_data["hotel_details"]:
                if isinstance(item, dict):
                    for k,v in item.items(): item[k] = str(v) # Convert all hotel values to strings

        return {"structured_quotation_data": structured_data}

    except Exception as e:
        print(f"Error structuring data for PDF with LLM ({provider}): {e}")
        raw_output_on_general_exception = ""
        if 'response_data' in locals() and response_data: # Check if response_data exists
             raw_output_on_general_exception = str(response_data)
        return {"structured_quotation_data": {"error": f"LLM error during JSON generation: {e}", "raw_output": raw_output_on_general_exception}}


def generate_pdf_node(state: QuotationGenerationState):
    # ... (same as before) ...
    structured_data = state.get("structured_quotation_data")
    if not structured_data or "error" in structured_data:
        error_message = structured_data.get("error", "Unknown error before PDF generation")
        raw_output = structured_data.get("raw_output", "N/A") 
        print(f"Skipping PDF generation due to previous error: {error_message}")
        pdf, dejavu_loaded = create_error_pdf_instance()
        text_to_write = f"Error generating PDF: {error_message}\n\nLLM Raw Output:\n{raw_output}"
        if not dejavu_loaded:
            text_to_write = sanitize_for_standard_font(text_to_write)
        pdf.multi_cell(0, 10, text_to_write)
        return {"pdf_output_bytes": bytes(pdf.output(dest='S'))} 
    try:
        pdf_bytes = create_pdf_quotation_bytes(structured_data) 
        return {"pdf_output_bytes": pdf_bytes}
    except Exception as e:
        print(f"Critical error during PDF generation: {e}")
        pdf, dejavu_loaded = create_error_pdf_instance()
        text_to_write = f"Critical error during PDF file creation: {str(e)}"
        if not dejavu_loaded:
            text_to_write = sanitize_for_standard_font(text_to_write)
        pdf.multi_cell(0, 10, text_to_write)
        return {"pdf_output_bytes": bytes(pdf.output(dest='S'))}

# ... (rest of the file, workflow definition, and run_quotation_generation_graph remain the same) ...
workflow = StateGraph(QuotationGenerationState)
workflow.add_node("fetch_enquiry_and_vendor_reply", fetch_data_node)
workflow.add_node("parse_vendor_text", parse_vendor_reply_node)
workflow.add_node("structure_data_for_pdf", structure_data_for_pdf_node)
workflow.add_node("generate_pdf_document", generate_pdf_node)

workflow.set_entry_point("fetch_enquiry_and_vendor_reply")
workflow.add_edge("fetch_enquiry_and_vendor_reply", "parse_vendor_text")
workflow.add_edge("parse_vendor_text", "structure_data_for_pdf")
workflow.add_edge("structure_data_for_pdf", "generate_pdf_document")
workflow.add_edge("generate_pdf_document", END)

quotation_generation_graph_compiled = workflow.compile()

def run_quotation_generation_graph(enquiry_details: dict, vendor_reply_text: str, provider: str) -> tuple[bytes, Dict[str, Any] | None]:
    initial_state = QuotationGenerationState(
        enquiry_details=enquiry_details,
        vendor_reply_text=vendor_reply_text,
        parsed_vendor_info_text="",
        structured_quotation_data={},
        pdf_output_bytes=b"",
        ai_provider=provider
    )
    
    print(f"[Quotation Generation Graph] Starting PDF generation with {provider}...")
    final_state = {} 
    
    try:
        final_state = quotation_generation_graph_compiled.invoke(initial_state)
        pdf_bytes = final_state.get("pdf_output_bytes")
        structured_data = final_state.get("structured_quotation_data", {}) 

        error_pdf_message = None
        if not pdf_bytes: 
            error_pdf_message = "Error: PDF generation failed, no bytes returned from graph unexpectedly."
        elif "error" in structured_data: 
             error_pdf_message = f"Error in structured data: {structured_data.get('error')}"
        
        if error_pdf_message:
            print(f"[Quotation Generation Graph] Warning: {error_pdf_message}")
            raw_output = structured_data.get("raw_output", "N/A")
            if not (pdf_bytes and (b"Error generating PDF" in pdf_bytes or b"Critical error during PDF" in pdf_bytes)):
                pdf, dejavu_loaded = create_error_pdf_instance()
                text_to_write = f"{error_pdf_message}\n\nLLM Raw Output:\n{raw_output}"
                if not dejavu_loaded:
                    text_to_write = sanitize_for_standard_font(text_to_write)
                pdf.multi_cell(0, 10, text_to_write)
                pdf_bytes = bytes(pdf.output(dest='S'))
            return pdf_bytes, structured_data
        
        print("[Quotation Generation Graph] PDF generation process completed.")
        return pdf_bytes, structured_data
        
    except Exception as e:
        print(f"[Quotation Generation Graph] Critical error running quotation graph ({provider}): {e}")
        raw_output_from_final_state = final_state.get("structured_quotation_data", {}).get("raw_output", "N/A")
        
        pdf, dejavu_loaded = create_error_pdf_instance()
        pdf.multi_cell(0, 8, sanitize_for_standard_font("Quotation Generation Failed Due to System Error") if not dejavu_loaded else "Quotation Generation Failed Due to System Error", align='C')
        pdf.ln(5)
        
        if dejavu_loaded:
            pdf.set_font("DejaVu", "", 10) 
        else:
            pdf.set_font("Helvetica", "", 10)

        details_text = f"Details: {str(e)}\n\nLLM Raw Output (if available from last successful node):\n{raw_output_from_final_state}"
        if not dejavu_loaded:
            details_text = sanitize_for_standard_font(details_text)
        pdf.multi_cell(0, 5, details_text)
        
        return bytes(pdf.output(dest='S')), {"error": f"Graph execution system error: {str(e)}", "raw_output": raw_output_from_final_state}