# src/core/itinerary_generator.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.exceptions import OutputParserException, LangChainException
from src.llm.llm_providers import get_llm_instance
from src.llm.llm_prompts import PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING
import httpx # For HTTPStatusError

def generate_places_suggestion_llm(enquiry_details: dict, provider: str) -> tuple[str | None, dict | None]:
    """
    Generates a list of suggested places/attractions using Langchain.
    Returns a tuple: (suggestion_text, error_info_dict).
    suggestion_text is None if an error occurred.
    error_info_dict contains 'message' and optionally 'details', 'status_code', 'raw_response', 'type' if an error occurred.
    """
    try:
        llm = get_llm_instance(provider) # This can raise ValueError for bad provider or missing keys
        prompt_template = ChatPromptTemplate.from_template(PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING)
        output_parser = StrOutputParser()
        chain = prompt_template | llm | output_parser
        
        response = chain.invoke(enquiry_details)
        return response, None
    
    except ValueError as ve: # Catch errors from get_llm_instance (e.g. API key missing)
        error_msg = f"Configuration error for LLM provider {provider}: {ve}"
        print(error_msg)
        return None, {"message": error_msg, "details": str(ve), "type": "ConfigurationError"}

    except httpx.HTTPStatusError as hse:
        error_msg = f"LLM provider HTTP error ({provider}): Status {hse.response.status_code} - {hse.response.reason_phrase}"
        raw_response_content = None
        try:
            # Try to parse JSON, but fallback to text if it's not JSON
            raw_response_content = hse.response.json() 
        except Exception:
            raw_response_content = hse.response.text
        
        print(f"{error_msg}. Response: {raw_response_content}")
        
        # Try to extract a more specific message from common error structures
        provider_message = str(raw_response_content)
        if isinstance(raw_response_content, dict):
            if "error" in raw_response_content and isinstance(raw_response_content["error"], dict) and "message" in raw_response_content["error"]:
                provider_message = raw_response_content["error"]["message"]
            elif "message" in raw_response_content:
                 provider_message = raw_response_content["message"]


        return None, {
            "message": f"The AI service ({provider}) returned an HTTP error (Status: {hse.response.status_code}).",
            "details": f"Provider message: {provider_message}",
            "status_code": hse.response.status_code,
            "raw_response": str(raw_response_content), # Ensure it's a string for display
            "type": "HttpError"
        }
    
    except OutputParserException as ope:
        error_msg = f"Error parsing LLM output ({provider}): {ope}"
        print(error_msg)
        return None, {"message": "The AI's response could not be understood or parsed correctly.", "details": str(ope), "type": "OutputParsingError"}

    except LangChainException as lce: 
        error_msg = f"LangChain error during place suggestions with LLM ({provider}): {lce}"
        print(error_msg)
        details = str(lce)
        if hasattr(lce, 'args') and lce.args:
            if isinstance(lce.args[0], str) and ("APIConnectionError" in lce.args[0] or "APIError" in lce.args[0] or "RateLimitError" in lce.args[0]):
                 details = lce.args[0]

        return None, {"message": f"An AI processing error occurred with {provider}.", "details": details, "type": "LangChainException"}

    except Exception as e:
        error_msg = f"Unexpected error generating place suggestions with LLM ({provider}): {type(e).__name__} - {e}"
        print(error_msg)
        # This block for OpenRouter might be redundant if LangChain's OpenRouter integration
        # already raises specific LangChainException or HTTPStatusError caught above.
        if provider == "OpenRouter" and hasattr(e, 'response') and hasattr(e.response, 'json'):
            try:
                error_data = e.response.json()
                if 'error' in error_data and isinstance(error_data['error'], dict) and 'message' in error_data['error']:
                    openrouter_msg = error_data['error']['message']
                    return None, {
                        "message": f"OpenRouter specific API error: {openrouter_msg}",
                        "details": str(error_data),
                        "type": "OpenRouterAPIError"
                    }
            except Exception:
                pass # Fallback to generic if JSON parsing or structure access fails
        return None, {"message": f"An unexpected error occurred while contacting the AI service ({provider}).", "details": str(e), "type": "GenericError"}