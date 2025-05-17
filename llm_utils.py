# llm_utils.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict

load_dotenv()

def get_llm_instance(provider: str):
    """
    Returns an LLM instance based on the specified provider.
    """
    if provider == "Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        print(f"LLM_UTILS (get_llm_instance for Gemini): GOOGLE_API_KEY {'FOUND' if api_key else 'NOT FOUND'}")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Gemini. Check .env file and ensure it's loaded.")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key)
    elif provider == "OpenRouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        # Default to a common model if not specified in .env, or let OpenRouter decide if model_name is None
        model_name = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5") 
        print(f"LLM_UTILS (get_llm_instance for OpenRouter): OPENROUTER_API_KEY {'FOUND' if api_key else 'NOT FOUND'}, Model: {model_name}")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found for OpenRouter. Check .env file and ensure it's loaded.")
        # Get HTTP_REFERER and X_TITLE from environment variables or use defaults
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000") # Replace with your actual site URL
        app_title = os.getenv("OPENROUTER_APP_TITLE", "AI Travel Quotation") # Replace with your actual app name

        # Explicitly set Authorization header for OpenRouter
        headers = {
            "HTTP-Referer": http_referer,
            "X-Title": app_title,
        }

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key, # Pass the API key directly to the client
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}. Supported providers are 'Gemini', 'OpenRouter'.")

def generate_places_suggestion_llm(enquiry_details: dict, provider: str) -> str:
    """
    Generates a list of suggested places/attractions using Langchain with the specified provider.
    """
    try:
        llm = get_llm_instance(provider)
        prompt_template = ChatPromptTemplate.from_messages([
            ("human", """You are a helpful travel assistant. 
Based on the following enquiry, suggest a list of key places, attractions, or activities to cover. Do not create a day-wise plan. Just list the suggestions.

Enquiry:
- Destination: {destination}
- Duration: {num_days} days
- Travelers: {traveler_count}
- Trip Type: {trip_type}

Provide the output as a comma-separated list or a bulleted list of suggestions.""")
        ])
        output_parser = StrOutputParser()
        chain = prompt_template | llm | output_parser
        
        response = chain.invoke(enquiry_details)
        return response
    except Exception as e:
        print(f"Error generating place suggestions with LLM ({provider}): {e}")
        return f"Error: Could not generate place suggestions using {provider}. Detail: {e}"

# --- LangGraph for Quotation Generation ---

class QuotationState(TypedDict):
    enquiry_details: dict
    vendor_reply_text: str
    parsed_vendor_info: dict
    final_quotation: str
    ai_provider: str # To know which LLM to use in nodes

def fetch_data_node(state: QuotationState):
    print("---FETCHING DATA (Passed in initial state)---")
    # Data is already in state, this node mainly acts as an entry point or could fetch additional data if needed.
    # We ensure ai_provider is part of the state passed along.
    return {
        "enquiry_details": state["enquiry_details"],
        "vendor_reply_text": state["vendor_reply_text"],
        "ai_provider": state["ai_provider"] 
    }

def parse_vendor_reply_node(state: QuotationState):
    print(f"---PARSING VENDOR REPLY ({state['ai_provider']})---")
    vendor_reply = state["vendor_reply_text"]
    enquiry_details = state["enquiry_details"]
    provider = state["ai_provider"]

    try:
        llm = get_llm_instance(provider)
        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are an expert at parsing vendor replies for travel quotations. 
From the vendor reply provided below, extract the following information:
1.  **Proposed Itinerary:** (Extract the day-by-day plan or sequence of activities if available. If not explicitly day-wise, extract the described tour flow. If no itinerary, state 'Itinerary not specified by vendor.')
2.  **Total Price:** (e.g., USD 1200, INR 50000. If not found, state 'Not specified'.)
3.  **Inclusions:** (List them. If not found, state 'Not specified'.)
4.  **Exclusions:** (List them. If not found, state 'Not specified'.)

Vendor Reply:
---
{vendor_reply}
---

Enquiry Context (for your reference, if needed to understand the reply):
- Destination: {destination}
- Duration: {num_days} days

Output the extracted information clearly, for example:
Itinerary:
Day 1: ...
Day 2: ...
Price: ...
Inclusions:
- ...
Exclusions:
- ...
""")
        ])
        parser = StrOutputParser()
        chain = prompt | llm | parser
        
        parsed_info_str = chain.invoke({
            "vendor_reply": vendor_reply,
            "destination": enquiry_details.get("destination"),
            "num_days": enquiry_details.get("num_days")
        })
        return {"parsed_vendor_info": {"full_details_from_vendor": parsed_info_str}}

    except Exception as e:
        print(f"Error parsing vendor reply with LLM ({provider}): {e}")
        return {"parsed_vendor_info": {"full_details_from_vendor": f"Error parsing vendor reply using {provider}. Detail: {e}"}}


def combine_and_format_node(state: QuotationState):
    print(f"---COMBINING AND FORMATTING QUOTATION ({state['ai_provider']})---")
    enquiry = state["enquiry_details"]
    provider = state["ai_provider"]
    
    parsed_vendor_info_dict = state.get("parsed_vendor_info", {})
    vendor_extracted_details = parsed_vendor_info_dict.get("full_details_from_vendor", "Vendor details not available or parsing failed.")

    try:
        llm = get_llm_instance(provider)
        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are a travel agent creating a client quotation.
Use the **details extracted from the vendor's reply** to construct the quotation. This includes the itinerary, pricing, inclusions, and exclusions provided by the vendor.

Client Enquiry Details (for context and salutation):
- Destination: {destination}
- Number of Days: {num_days}
- Traveler Count: {traveler_count}
- Trip Type: {trip_type}

Vendor's Proposed Details (Itinerary, Price, Inclusions, Exclusions):
---
{vendor_extracted_details}
---

Format the quotation professionally and clearly. Start with a greeting, include the trip overview based on the enquiry, then present the vendor's proposed itinerary and commercial details. End with a closing remark.
If the vendor details mention 'Not specified' for any section, reflect that appropriately.
""")
        ])
        parser = StrOutputParser()
        chain = prompt | llm | parser

        final_quotation_text = chain.invoke({
            "destination": enquiry.get("destination", "N/A"),
            "num_days": enquiry.get("num_days", "N/A"),
            "traveler_count": enquiry.get("traveler_count", "N/A"),
            "trip_type": enquiry.get("trip_type", "N/A"),
            "vendor_extracted_details": vendor_extracted_details
        })
        return {"final_quotation": final_quotation_text}
    except Exception as e:
        print(f"Error formatting final quotation with LLM ({provider}): {e}")
        return {"final_quotation": f"Error generating final quotation using {provider}. Detail: {e}"}

# Define the graph
workflow = StateGraph(QuotationState)

workflow.add_node("fetch_data", fetch_data_node)
workflow.add_node("parse_vendor", parse_vendor_reply_node)
workflow.add_node("format_quotation", combine_and_format_node)

workflow.set_entry_point("fetch_data")
workflow.add_edge("fetch_data", "parse_vendor")
workflow.add_edge("parse_vendor", "format_quotation")
workflow.add_edge("format_quotation", END)

quotation_generation_graph = workflow.compile()

def run_quotation_generation_graph(enquiry_details: dict, vendor_reply_text: str, provider: str) -> str:
    initial_state = {
        "enquiry_details": enquiry_details,
        "vendor_reply_text": vendor_reply_text,
        "parsed_vendor_info": {},
        "final_quotation": "",
        "ai_provider": provider # Pass the selected provider to the graph state
    }
    try:
        final_state = quotation_generation_graph.invoke(initial_state)
        return final_state.get("final_quotation", f"Error: Quotation not generated ({provider}).")
    except Exception as e:
        print(f"Error running quotation graph ({provider}): {e}")
        return f"Critical error in quotation generation graph ({provider}): {e}"