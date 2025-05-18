# src/core/quotation_graph_builder.py
import os
import json
import re 
import streamlit as st # Added for accessing session state
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.exceptions import OutputParserException, LangChainException
import httpx # For HTTPStatusError

from src.llm.llm_providers import get_llm_instance
from src.llm.llm_prompts import (
    VENDOR_REPLY_PARSING_PROMPT_TEMPLATE_STRING,
    QUOTATION_STRUCTURE_JSON_PROMPT_TEMPLATE_STRING
)
from src.utils.pdf_utils import create_pdf_quotation_bytes
from fpdf import FPDF

# --- Helper Function for Error Message Extraction ---
def _extract_error_message_from_payload(payload: Any) -> str | None:
    """Helper to extract a user-friendly error message from common error structures."""
    if isinstance(payload, dict):
        if "error" in payload:
            error_content = payload["error"]
            if isinstance(error_content, dict) and "message" in error_content:
                return error_content["message"]
            elif isinstance(error_content, str): # Sometimes error is just a string
                return error_content
        elif "message" in payload: # Another common pattern
            return payload["message"]
    elif isinstance(payload, str): # If the payload itself is a string error
        return payload
    return None

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
    ai_suggested_itinerary_text: str 
    parsed_vendor_info_text: str 
    parsed_vendor_info_error: Dict[str, Any] | None 
    structured_quotation_data: Dict[str, Any] 
    pdf_output_bytes: bytes
    ai_provider: str

def fetch_data_node(state: QuotationGenerationState):
    return {
        "enquiry_details": state["enquiry_details"],
        "vendor_reply_text": state["vendor_reply_text"],
        "ai_suggested_itinerary_text": state["ai_suggested_itinerary_text"],
        "ai_provider": state["ai_provider"],
        "parsed_vendor_info_error": None, # Initialize error state for this stage
        "structured_quotation_data": {} # Initialize for this stage
    }

def parse_vendor_reply_node(state: QuotationGenerationState):
    vendor_reply = state["vendor_reply_text"]
    enquiry_details = state["enquiry_details"]
    provider = state["ai_provider"]
    error_payload = None # This will hold the final error dict for the state
    parsed_info_str = ""

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
    except ValueError as ve: 
        user_message = f"LLM Configuration Error ({provider}) during vendor reply parsing: {ve}"
        print(user_message)
        error_payload = {"message": user_message, "details": str(ve), "type": "ConfigurationError", "raw_response": None, "status_code": None}
    except httpx.HTTPStatusError as hse:
        raw_response_str = hse.response.text
        user_message = f"The AI service ({provider}) returned an HTTP error (Status: {hse.response.status_code}) during vendor reply parsing."
        provider_extracted_message = raw_response_str # Default
        try:
            raw_json = hse.response.json()
            msg_from_payload = _extract_error_message_from_payload(raw_json)
            if msg_from_payload:
                provider_extracted_message = msg_from_payload
                user_message = f"The AI service ({provider}) reported (Status {hse.response.status_code}): {provider_extracted_message}"
        except json.JSONDecodeError:
            pass # Keep raw string as provider_extracted_message
        
        print(f"GraphNode: HTTPStatusError (vendor reply, {provider}) - UserMsg: {user_message}, Raw: {raw_response_str}")
        error_payload = {
            "message": user_message,
            "details": f"Full details: {raw_response_str}",
            "raw_response": raw_response_str, 
            "type": "HttpError", 
            "status_code": hse.response.status_code
        }
    except OutputParserException as ope:
        user_message = f"LLM Output Parsing Error ({provider}) during vendor reply: {ope}"
        print(user_message)
        error_payload = {"message": user_message, "details": str(ope), "type": "OutputParsingError", "raw_response": None, "status_code": None}
    except LangChainException as lce:
        user_message = f"An AI processing error occurred with {provider} during vendor reply parsing."
        details_for_log = str(lce)
        error_type_for_log = "LangChainException"
        status_code_for_log = None
        raw_response_for_log = None

        if hasattr(lce, 'args') and lce.args:
            arg0 = lce.args[0]
            if isinstance(arg0, str):
                try:
                    if "status_code=" in arg0 and "response=" in arg0:
                        status_match = re.search(r"status_code=(\d+)", arg0)
                        if status_match: status_code_for_log = int(status_match.group(1))
                        
                        json_start_index = arg0.find("b'{") # Works for b'{"..."}'
                        if json_start_index == -1 : json_start_index = arg0.find("response='{") # Works for response='{"..."}'
                        if json_start_index != -1 :
                            # Adjust based on actual prefix (b' or response=')
                            prefix_len = 2 if arg0[json_start_index:json_start_index+2] == "b'" else len("response='")
                            
                            # Find the end of the JSON-like string
                            # This is heuristic, might need refinement for complex escaped strings
                            temp_str = arg0[json_start_index + prefix_len:]
                            balance = 0
                            end_json_index = -1
                            for i, char in enumerate(temp_str):
                                if char == '{': balance +=1
                                elif char == '}': balance -=1
                                if balance == 0 and char == '}': # found the end of the main JSON object
                                    end_json_index = i
                                    break
                            if end_json_index != -1:
                                json_like_str = temp_str[:end_json_index+1]
                                json_like_str = json_like_str.replace("\\'", "'") # Simple unescape for internal quotes
                                
                                error_payload_dict = json.loads(json_like_str)
                                raw_response_for_log = json.dumps(error_payload_dict)
                                extracted_provider_msg = _extract_error_message_from_payload(error_payload_dict)
                                if extracted_provider_msg:
                                    user_message = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                                    details_for_log = json.dumps(error_payload_dict)
                                    error_type_for_log = "ProviderAPIError"
                except (json.JSONDecodeError, IndexError, TypeError, re.error) as parse_err:
                    print(f"QuotationGraphBuilder: Could not parse detailed error from LangChainException args (vendor reply): {parse_err}")
                details_for_log = arg0 # Fallback if parsing fails
            elif isinstance(arg0, dict):
                raw_response_for_log = json.dumps(arg0)
                extracted_provider_msg = _extract_error_message_from_payload(arg0)
                if extracted_provider_msg:
                    user_message = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                    details_for_log = json.dumps(arg0)
                    error_type_for_log = "ProviderAPIError"
        
        print(f"GraphNode: LangChainExc (vendor reply, {provider}) - UserMsg: {user_message}, Details: {details_for_log}")
        error_payload = {
            "message": user_message, "details": details_for_log, "raw_response": raw_response_for_log,
            "type": error_type_for_log, "status_code": status_code_for_log
        }
    except Exception as e:
        user_message = f"Unexpected Error ({provider}) parsing vendor reply: {e}"
        print(user_message)
        error_payload = {"message": user_message, "details": str(e), "type": "GenericError", "raw_response": None, "status_code": None}
    
    if error_payload:
        return {"parsed_vendor_info_text": f"Error: {error_payload['message']}", "parsed_vendor_info_error": error_payload}
    
    return {"parsed_vendor_info_text": parsed_info_str, "parsed_vendor_info_error": None}


def structure_data_for_pdf_node(state: QuotationGenerationState):
    if state.get("parsed_vendor_info_error"):
        error_info = state["parsed_vendor_info_error"]
        err_msg = f"Skipped JSON structuring due to earlier vendor reply parsing error: {error_info.get('message')}"
        print(err_msg)
        return {"structured_quotation_data": {
            "error": err_msg,
            "details": error_info.get('details'),
            "raw_output": error_info.get('raw_response'),
            "type": "UpstreamError"
        }}

    enquiry = state["enquiry_details"]
    vendor_parsed_text = state["parsed_vendor_info_text"]
    ai_suggested_itinerary_text = state["ai_suggested_itinerary_text"]
    provider = state["ai_provider"]
    
    structured_data_payload = {} 
    raw_llm_output_for_error = ""
    
    try:
        llm = get_llm_instance(provider)
        num_days_int = int(enquiry.get("num_days", 0))
        num_nights = num_days_int - 1 if num_days_int > 0 else 0
        json_prompt_str = QUOTATION_STRUCTURE_JSON_PROMPT_TEMPLATE_STRING
        current_model_name = st.session_state.app_state.ai_config.selected_model_for_provider or ""

        if provider == "OpenRouter" and ("gpt" in current_model_name.lower() or \
                                         "claude-3" in current_model_name.lower()):
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
            "ai_suggested_itinerary_text": ai_suggested_itinerary_text,
            "vendor_parsed_text": vendor_parsed_text
        })

        if isinstance(response_data, str):
            raw_llm_output_for_error = response_data
            match = re.search(r"```json\s*(\{.*?\})\s*```", response_data, re.DOTALL)
            if match: potential_json_str = match.group(1)
            else: 
                cleaned_response = response_data.strip()
                json_start_index = cleaned_response.find('{')
                if json_start_index == -1: raise json.JSONDecodeError("No JSON object found.", cleaned_response, 0)
                open_braces = 0; json_end_index = -1
                for i in range(json_start_index, len(cleaned_response)):
                    if cleaned_response[i] == '{': open_braces += 1
                    elif cleaned_response[i] == '}':
                        open_braces -= 1
                        if open_braces == 0: json_end_index = i; break
                if json_end_index == -1: raise json.JSONDecodeError("Incomplete JSON object.", cleaned_response, 0)
                potential_json_str = cleaned_response[json_start_index : json_end_index + 1]
            structured_data_payload = json.loads(potential_json_str)
        elif isinstance(response_data, dict): 
            structured_data_payload = response_data
            raw_llm_output_for_error = json.dumps(response_data, indent=2)
        else:
            raise TypeError(f"Unexpected LLM output type for JSON: {type(response_data)}")

        for key_list in ["inclusions", "exclusions", "standard_exclusions_list", "important_notes"]:
            if key_list in structured_data_payload and isinstance(structured_data_payload[key_list], list):
                structured_data_payload[key_list] = [str(item) for item in structured_data_payload[key_list]]
        if "detailed_itinerary" in structured_data_payload and isinstance(structured_data_payload["detailed_itinerary"], list):
            for item in structured_data_payload["detailed_itinerary"]:
                if isinstance(item, dict):
                    for k,v in item.items(): item[k] = str(v)
        if "hotel_details" in structured_data_payload and isinstance(structured_data_payload["hotel_details"], list):
            for item in structured_data_payload["hotel_details"]:
                if isinstance(item, dict):
                    for k,v in item.items(): item[k] = str(v)

    except ValueError as ve: 
        user_message = f"LLM Configuration Error ({provider}) during JSON structuring: {ve}"
        print(user_message)
        structured_data_payload = {"error": user_message, "details": str(ve), "type": "ConfigurationError", "raw_output": raw_llm_output_for_error, "status_code": None}
    except httpx.HTTPStatusError as hse:
        raw_response_str = hse.response.text
        if not raw_llm_output_for_error: raw_llm_output_for_error = raw_response_str
        user_message = f"The AI service ({provider}) returned an HTTP error (Status: {hse.response.status_code}) during JSON structuring."
        provider_extracted_message = raw_response_str
        try:
            raw_json = hse.response.json()
            msg_from_payload = _extract_error_message_from_payload(raw_json)
            if msg_from_payload:
                provider_extracted_message = msg_from_payload
                user_message = f"The AI service ({provider}) reported (Status {hse.response.status_code}): {provider_extracted_message}"
        except json.JSONDecodeError:
            pass
        print(f"GraphNode: HTTPStatusError (JSON structuring, {provider}) - UserMsg: {user_message}, Raw: {raw_response_str}")
        structured_data_payload = {
            "error": user_message, "details": f"Full details: {raw_response_str}", 
            "raw_output": raw_response_str, "type": "HttpError", "status_code": hse.response.status_code
        }
    except (json.JSONDecodeError, OutputParserException) as jpe:
        user_message = f"LLM JSON Parsing Error ({provider}): {jpe}. Preview: '{str(raw_llm_output_for_error)[:200]}...'"
        print(user_message)
        structured_data_payload = {"error": user_message, "details": str(jpe), "raw_output": raw_llm_output_for_error, "type": "JsonParsingError", "status_code": None}
    except LangChainException as lce:
        user_message = f"An AI processing error occurred with {provider} during JSON structuring."
        details_for_log = str(lce)
        error_type_for_log = "LangChainException"
        status_code_for_log = None
        # raw_llm_output_for_error will be used as raw_response_for_log if populated

        if hasattr(lce, 'args') and lce.args:
            arg0 = lce.args[0]
            if isinstance(arg0, str):
                try:
                    if "status_code=" in arg0 and "response=" in arg0: # Check for LangChain's wrapped httpx error string
                        status_match = re.search(r"status_code=(\d+)", arg0)
                        if status_match: status_code_for_log = int(status_match.group(1))
                        json_start_index = arg0.find("b'{")
                        if json_start_index == -1 : json_start_index = arg0.find("response='{")
                        if json_start_index != -1 :
                            prefix_len = 2 if arg0[json_start_index:json_start_index+2] == "b'" else len("response='")
                            temp_str = arg0[json_start_index + prefix_len:]
                            balance = 0; end_json_index = -1
                            for i, char in enumerate(temp_str):
                                if char == '{': balance +=1
                                elif char == '}': balance -=1
                                if balance == 0 and char == '}': end_json_index = i; break
                            if end_json_index != -1:
                                json_like_str = temp_str[:end_json_index+1].replace("\\'", "'")
                                error_payload_dict = json.loads(json_like_str)
                                if not raw_llm_output_for_error: raw_llm_output_for_error = json.dumps(error_payload_dict) # Capture this as raw if not already set
                                extracted_provider_msg = _extract_error_message_from_payload(error_payload_dict)
                                if extracted_provider_msg:
                                    user_message = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                                    details_for_log = json.dumps(error_payload_dict)
                                    error_type_for_log = "ProviderAPIError"
                except (json.JSONDecodeError, IndexError, TypeError, re.error) as parse_err:
                    print(f"QuotationGraphBuilder: Could not parse detailed error from LangChainException args (JSON structuring): {parse_err}")
                if details_for_log == str(lce) : details_for_log = arg0 # If not updated by parsing, use arg0
            elif isinstance(arg0, dict):
                if not raw_llm_output_for_error: raw_llm_output_for_error = json.dumps(arg0)
                extracted_provider_msg = _extract_error_message_from_payload(arg0)
                if extracted_provider_msg:
                    user_message = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                    details_for_log = json.dumps(arg0)
                    error_type_for_log = "ProviderAPIError"
        
        print(f"GraphNode: LangChainExc (JSON structuring, {provider}) - UserMsg: {user_message}, Details: {details_for_log}")
        structured_data_payload = {
            "error": user_message, "details": details_for_log, "raw_output": raw_llm_output_for_error,
            "type": error_type_for_log, "status_code": status_code_for_log
        }
    except Exception as e:
        user_message = f"Unexpected Error ({provider}) during JSON structuring: {type(e).__name__} - {e}"
        print(user_message)
        structured_data_payload = {"error": user_message, "details": str(e), "raw_output": raw_llm_output_for_error, "type": "GenericError", "status_code": None}
    
    return {"structured_quotation_data": structured_data_payload}


def generate_pdf_node(state: QuotationGenerationState):
    structured_data = state.get("structured_quotation_data")
    
    if not structured_data or "error" in structured_data:
        error_message = structured_data.get("error", "Unknown error before PDF generation")
        error_details = structured_data.get("details", "")
        raw_output = structured_data.get("raw_output", "N/A")
        error_type = structured_data.get("type", "UnknownError")
        print(f"Error PDF to be generated due to: {error_type} - {error_message}")
        
        pdf, dejavu_loaded = create_error_pdf_instance()
        title = "Quotation Generation Failed"
        if error_type == "UpstreamError": title = "Quotation Generation Failed: Data Parsing Error"
        elif error_type in ["ConfigurationError", "HttpError", "LangChainException", "JsonParsingError", "ProviderAPIError"]: 
            title = f"Quotation Generation Failed: AI ({state.get('ai_provider')}) Error"

        text_to_write = f"{title}\n\nIssue: {error_message}"
        if error_details and error_details != error_message : text_to_write += f"\nDetails: {error_details}"
        if raw_output and raw_output != "N/A" and isinstance(raw_output, str) and len(raw_output.strip()) > 0:
            text_to_write += f"\n\nTechnical Information (e.g., AI Raw Output):\n{str(raw_output)[:1000]}"
        
        if not dejavu_loaded: text_to_write = sanitize_for_standard_font(text_to_write)
        pdf.multi_cell(0, 7, text_to_write)
        return {"pdf_output_bytes": bytes(pdf.output(dest='S'))}
    
    try:
        pdf_bytes = create_pdf_quotation_bytes(structured_data)
        return {"pdf_output_bytes": pdf_bytes}
    except Exception as e: 
        print(f"Critical error during PDF rendering process: {e}")
        pdf, dejavu_loaded = create_error_pdf_instance()
        text_to_write = f"Critical Error During PDF File Creation\n\nDetails: {str(e)}\n\nThis error occurred after the AI successfully structured the data. Please check the PDF library and data."
        if not dejavu_loaded: text_to_write = sanitize_for_standard_font(text_to_write)
        pdf.multi_cell(0, 7, text_to_write)
        return {"pdf_output_bytes": bytes(pdf.output(dest='S'))}

# Workflow definition
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


def run_quotation_generation_graph(
    enquiry_details: dict,
    vendor_reply_text: str,
    ai_suggested_itinerary_text: str,
    provider: str
) -> tuple[bytes | None, Dict[str, Any] | None]:
    initial_state = QuotationGenerationState(
        enquiry_details=enquiry_details,
        vendor_reply_text=vendor_reply_text,
        ai_suggested_itinerary_text=ai_suggested_itinerary_text,
        parsed_vendor_info_text="",
        parsed_vendor_info_error=None,
        structured_quotation_data={},
        pdf_output_bytes=b"",
        ai_provider=provider
    )

    print(f"[Quotation Generation Graph] Starting quotation data generation with {provider}...")
    final_state = {}
    pdf_bytes = None
    structured_data = None

    try:
        final_state = quotation_generation_graph_compiled.invoke(initial_state)
        pdf_bytes = final_state.get("pdf_output_bytes")
        structured_data = final_state.get("structured_quotation_data", {})

        if not pdf_bytes: 
             print("[Quotation Generation Graph] CRITICAL: PDF generation node returned no bytes.")
             err_pdf_fallback, dl = create_error_pdf_instance()
             emsg = "System Error: PDF Generation process failed to produce output."
             if not dl: emsg = sanitize_for_standard_font(emsg)
             err_pdf_fallback.multi_cell(0, 10, emsg)
             pdf_bytes = bytes(err_pdf_fallback.output(dest='S'))
             if not structured_data.get("error"): 
                structured_data = {"error": "System Error: PDF Generation process failed.", 
                                   "details": "No PDF bytes returned from graph's PDF node.", 
                                   "type": "SystemError", "raw_output": None, "status_code": None}
        
        print("[Quotation Generation Graph] Graph execution completed.")
        return pdf_bytes, structured_data

    except Exception as e: 
        print(f"[Quotation Generation Graph] CRITICAL error running compiled graph for {provider}: {e}")
        err_msg_graph = f"System error during quotation graph execution: {str(e)}"
        raw_out_context = final_state.get("structured_quotation_data", {}).get("raw_output")
        if not raw_out_context: raw_out_context = final_state.get("parsed_vendor_info_text", "N/A")

        err_pdf, dl = create_error_pdf_instance()
        title = "Quotation Generation Failed: System Error"
        details_text = f"Error: {str(e)}\n\nContext (if available):\n{raw_out_context}"
        if not dl: 
            title = sanitize_for_standard_font(title)
            details_text = sanitize_for_standard_font(details_text)
        
        err_pdf.multi_cell(0, 8, title, align='C'); err_pdf.ln(5)
        if dl: err_pdf.set_font("DejaVu", "", 10)
        else: err_pdf.set_font("Helvetica", "", 10)
        err_pdf.multi_cell(0, 5, details_text)
        
        return bytes(err_pdf.output(dest='S')), {
            "error": err_msg_graph, "details": str(e), "raw_output": raw_out_context, 
            "type": "GraphExecutionError", "status_code": None
        }