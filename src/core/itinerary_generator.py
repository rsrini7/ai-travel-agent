# src/core/itinerary_generator.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.exceptions import OutputParserException, LangChainException
from src.llm.llm_providers import get_llm_instance
from src.llm.llm_prompts import PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING
import httpx # For HTTPStatusError
import json # For parsing JSON error responses
import re # For parsing generic exception strings
from typing import Any

def _extract_error_message_from_payload(payload: Any) -> str | None:
    """Helper to extract a user-friendly error message from common error structures."""
    if isinstance(payload, dict):
        if "error" in payload:
            error_content = payload["error"]
            if isinstance(error_content, dict) and "message" in error_content:
                return error_content["message"]
            elif isinstance(error_content, str):
                return error_content
        elif "message" in payload:
            return payload["message"]
    elif isinstance(payload, str):
        return payload
    return None


def generate_places_suggestion_llm(enquiry_details: dict, provider: str, ai_conf: Any) -> tuple[str | None, dict | None]: # Added ai_conf
    """
    Generates a list of suggested places/attractions using Langchain.
    Returns a tuple: (suggestion_text, error_info_dict).
    suggestion_text is None if an error occurred.
    error_info_dict contains 'message' and optionally 'details', 'status_code', 'raw_response', 'type' if an error occurred.
    """
    try:
        llm = get_llm_instance(provider, ai_conf) # Passed ai_conf
        prompt_template = ChatPromptTemplate.from_template(PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING)
        output_parser = StrOutputParser()
        chain = prompt_template | llm | output_parser
        
        response = chain.invoke(enquiry_details)
        return response, None
    
    except ValueError as ve:
        error_msg = f"Configuration error for LLM provider {provider}: {ve}"
        print(error_msg)
        return None, {"message": error_msg, "details": str(ve), "type": "ConfigurationError"}

    except httpx.HTTPStatusError as hse:
        error_msg_user_facing = f"The AI service ({provider}) returned an HTTP error (Status: {hse.response.status_code})."
        raw_response_content_str = hse.response.text
        provider_extracted_message = raw_response_content_str 

        try:
            raw_response_json = hse.response.json()
            msg_from_payload = _extract_error_message_from_payload(raw_response_json)
            if msg_from_payload:
                provider_extracted_message = msg_from_payload
                error_msg_user_facing = f"The AI service ({provider}) reported (Status {hse.response.status_code}): {provider_extracted_message}"
        except json.JSONDecodeError:
            pass
        
        print(f"HTTPStatusError ({provider}) - UserMsg: {error_msg_user_facing}. Raw: {raw_response_content_str}")
        
        return None, {
            "message": error_msg_user_facing,
            "details": f"Full details: {raw_response_content_str}",
            "status_code": hse.response.status_code,
            "raw_response": raw_response_content_str,
            "type": "HttpError"
        }
    
    except OutputParserException as ope:
        error_msg = f"Error parsing LLM output ({provider}): {ope}"
        print(error_msg)
        return None, {"message": "The AI's response could not be understood or parsed correctly.", "details": str(ope), "type": "OutputParsingError"}

    except LangChainException as lce:
        error_msg_user_facing = f"An AI processing error occurred with {provider}."
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
                        
                        json_start_idx_b = arg0.find("b'{")
                        json_start_idx_plain = arg0.find("response='{")

                        json_start_idx = -1
                        prefix_len = 0

                        if json_start_idx_b != -1:
                            json_start_idx = json_start_idx_b
                            prefix_len = 2 # for b'
                        elif json_start_idx_plain != -1:
                            json_start_idx = json_start_idx_plain
                            prefix_len = len("response='")
                        
                        if json_start_idx != -1:
                            temp_str = arg0[json_start_idx + prefix_len:]
                            balance = 0; end_json_idx = -1
                            for i_char, char_val in enumerate(temp_str):
                                if char_val == '{': balance +=1
                                elif char_val == '}': balance -=1
                                if balance == 0 and char_val == '}': end_json_idx = i_char; break
                            
                            if end_json_idx != -1:
                                json_like_str = temp_str[:end_json_idx+1].replace("\\'", "'")
                                error_payload_dict = json.loads(json_like_str)
                                raw_response_for_log = json.dumps(error_payload_dict)
                                extracted_provider_msg = _extract_error_message_from_payload(error_payload_dict)
                                if extracted_provider_msg:
                                    error_msg_user_facing = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                                    details_for_log = json.dumps(error_payload_dict)
                                    error_type_for_log = "ProviderAPIError"
                except (json.JSONDecodeError, IndexError, TypeError, re.error) as parse_err:
                    print(f"Could not parse detailed error from LangChainException args: {parse_err}")
                if details_for_log == str(lce) : details_for_log = arg0 
            elif isinstance(arg0, dict):
                raw_response_for_log = json.dumps(arg0)
                extracted_provider_msg = _extract_error_message_from_payload(arg0)
                if extracted_provider_msg:
                    error_msg_user_facing = f"The AI service ({provider}) reported: {extracted_provider_msg}"
                    details_for_log = json.dumps(arg0)
                    error_type_for_log = "ProviderAPIError"

        print(f"LangChain error ({provider}) - Type: {error_type_for_log}, Message: {error_msg_user_facing}, Details: {details_for_log}")
        return None, {
            "message": error_msg_user_facing,
            "details": details_for_log,
            "raw_response": raw_response_for_log,
            "type": error_type_for_log,
            "status_code": status_code_for_log
        }
    except Exception as e: # Generic catch-all
        error_msg_generic_user = f"An unexpected error occurred while contacting the AI service ({provider})."
        error_details_generic = str(e)
        error_type_generic = "GenericError"
        status_code_generic = None
        raw_response_generic = None 

        exception_str = str(e)
        print(f"DEBUG: In generate_places_suggestion_llm - Generic Exception caught. str(e): {exception_str}") # DEBUG PRINT

        if provider == "Groq" and "BadRequestError" in exception_str and "{'error':" in exception_str:
            print(f"DEBUG: Groq BadRequestError string detected: {exception_str}") # DEBUG PRINT
            try:
                dict_start_index = exception_str.find("{'error':")
                print(f"DEBUG: dict_start_index: {dict_start_index}") # DEBUG PRINT
                if dict_start_index != -1:
                    dict_str_to_parse = exception_str[dict_start_index:]
                    print(f"DEBUG: dict_str_to_parse before ast.literal_eval: >>>{dict_str_to_parse}<<<") # DEBUG PRINT
                    
                    import ast
                    error_dict_from_str = ast.literal_eval(dict_str_to_parse)
                    print(f"DEBUG: ast.literal_eval successful. Parsed dict: {error_dict_from_str}") # DEBUG PRINT
                    raw_response_generic = json.dumps(error_dict_from_str) 
                    
                    extracted_msg = _extract_error_message_from_payload(error_dict_from_str)
                    if extracted_msg:
                        error_msg_generic_user = f"The AI service ({provider}) reported an issue: {extracted_msg}"
                        error_details_generic = json.dumps(error_dict_from_str, indent=2) 
                        error_type_generic = "ProviderReportedError" 
                        
                        status_part_of_exc_str = exception_str[:dict_start_index]
                        status_match = re.search(r"Error code:\s*(\d+)", status_part_of_exc_str, re.IGNORECASE)
                        if status_match:
                            status_code_generic = int(status_match.group(1))
                else: 
                    print(f"DEBUG: Groq BadRequestError detected, but could not find start of dict string.")

            except (SyntaxError, ValueError, ImportError, AttributeError) as parse_err:
                print(f"DEBUG: Could not parse dict from Groq BadRequestError string using ast.literal_eval: {parse_err}. String was: >>>{dict_str_to_parse if 'dict_str_to_parse' in locals() else 'UNKNOWN'}<<<") # DEBUG PRINT
                # Fallback if ast.literal_eval fails
                msg_match = re.search(r"'message':\s*'(.*?)'", exception_str)
                if msg_match:
                     error_msg_generic_user = f"Groq API Error (fallback): {msg_match.group(1)}"
                     error_type_generic = "GroqBadRequestErrorFallback"
        
        elif provider == "OpenRouter" and hasattr(e, 'response') and hasattr(e.response, 'json'):
            # ... (OpenRouter specific logic remains the same) ...
            try:
                error_data = e.response.json()
                raw_response_generic = json.dumps(error_data)
                extracted_or_msg = _extract_error_message_from_payload(error_data)
                if extracted_or_msg:
                    error_msg_generic_user = f"OpenRouter API error: {extracted_or_msg}"
                    error_details_generic = json.dumps(error_data)
                    error_type_generic = "OpenRouterAPIError"
                    if hasattr(e.response, 'status_code'): status_code_generic = e.response.status_code
            except Exception as openrouter_parse_err:
                print(f"Could not parse OpenRouter specific error: {openrouter_parse_err}")

        print(f"Unexpected error ({provider}) - Type: {error_type_generic}, Error: {type(e).__name__} - {e}")
        return None, {
            "message": error_msg_generic_user,
            "details": error_details_generic,
            "raw_response": raw_response_generic,
            "type": error_type_generic,
            "status_code": status_code_generic
        }