# itinerary_generator.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.llm.llm_providers import get_llm_instance
from src.llm.llm_prompts import PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING

def generate_places_suggestion_llm(enquiry_details: dict, provider: str) -> str:
    """
    Generates a list of suggested places/attractions using Langchain with the specified provider.
    """
    try:
        llm = get_llm_instance(provider)
        prompt_template = ChatPromptTemplate.from_template(PLACES_SUGGESTION_PROMPT_TEMPLATE_STRING)
        
        output_parser = StrOutputParser()
        chain = prompt_template | llm | output_parser
        
        response = chain.invoke(enquiry_details)
        return response
    except Exception as e:
        error_msg = f"Error generating place suggestions with LLM ({provider}): {e}"
        print(error_msg)
        if provider == "OpenRouter" and hasattr(e, 'response') and hasattr(e.response, 'json'):
            try:
                error_data = e.response.json()
                if 'error' in error_data and 'message' in error_data['error']:
                    return f"OpenRouter Model Error: {error_data['error']['message']}"
            except Exception: # Fallback if response is not JSON or structure is unexpected
                pass
        return f"Error: Could not generate place suggestions using {provider}. Detail: {str(e)}"