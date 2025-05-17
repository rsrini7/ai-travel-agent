# llm_utils.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict, List # Removed Annotated, operator

load_dotenv()

def get_llm_instance():
    api_key = os.getenv("GOOGLE_API_KEY")
    print(f"LLM_UTILS (get_llm_instance): Key from env: {api_key[:5]}...{api_key[-5:] if api_key and len(api_key) > 10 else ' (short or missing)'}")
    if not api_key:
        print("LLM_UTILS: GOOGLE_API_KEY not found, attempting to load .env again.")
        load_dotenv(override=True)
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables even after trying to reload. Check .env file.")
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key)

# MODIFIED: AI Itinerary Generation (Now for places/suggestions)
def generate_places_suggestion_llm(enquiry_details: dict) -> str:
    """
    Generates a list of suggested places/attractions using Langchain with Gemini.
    enquiry_details: dict like {'destination': 'Paris', 'num_days': 3, 'traveler_count': 2, 'trip_type': 'Leisure'}
    """
    try:
        llm = get_llm_instance()
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
        print(f"Error generating place suggestions with LLM (Gemini): {e}")
        return f"Error: Could not generate place suggestions. Detail: {e}"

# --- LangGraph for Quotation Generation ---

class QuotationState(TypedDict):
    enquiry_details: dict
    # itinerary_text: str # REMOVED - AI itinerary no longer directly used in quote
    vendor_reply_text: str
    parsed_vendor_info: dict # This will now include itinerary from vendor
    final_quotation: str

def fetch_data_node(state: QuotationState):
    print("---FETCHING DATA (Simulated, data passed in initial state)---")
    return {
        "enquiry_details": state["enquiry_details"],
        "vendor_reply_text": state["vendor_reply_text"]
        # "itinerary_text" is no longer passed here
    }

def parse_vendor_reply_node(state: QuotationState): # MODIFIED
    print("---PARSING VENDOR REPLY (GEMINI)---")
    vendor_reply = state["vendor_reply_text"]
    enquiry_details = state["enquiry_details"] # For context if needed by LLM

    try:
        llm = get_llm_instance()
        # MODIFIED PROMPT: Now asking to extract itinerary from vendor reply
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
        parser = StrOutputParser() # Keep as StrOutputParser, we'll parse the string output in the next step or rely on the LLM's structure
        chain = prompt | llm | parser
        
        # For structured output, you might consider JsonOutputParser, but for MVP StrOutputParser is fine
        # if the prompt is good at guiding the LLM to a consistent string format.
        parsed_info_str = chain.invoke({
            "vendor_reply": vendor_reply,
            "destination": enquiry_details.get("destination"),
            "num_days": enquiry_details.get("num_days")
        })
        # We expect the LLM to give a string. We'll pass this whole string
        # to the next node, or you could try to parse it here into a dict.
        # For simplicity, let's assume the next node can handle this string.
        # Or, better, let's try to make this node return a more structured dict.
        # This requires more robust parsing of parsed_info_str or a JsonOutputParser.
        # For now, let's keep it simple and assume the formatting node's LLM can work with this.
        
        # A more robust approach here would be to use another LLM call or regex to split parsed_info_str
        # into 'itinerary', 'price', 'inclusions', 'exclusions'.
        # For MVP, we can pass the whole string as "summary" and adjust the final formatting prompt.

        # Let's adjust the final formatting prompt to expect this combined string.
        return {"parsed_vendor_info": {"full_details_from_vendor": parsed_info_str}}

    except Exception as e:
        print(f"Error parsing vendor reply with LLM (Gemini): {e}")
        return {"parsed_vendor_info": {"full_details_from_vendor": f"Error parsing vendor reply. Detail: {e}"}}


def combine_and_format_node(state: QuotationState): # MODIFIED
    print("---COMBINING AND FORMATTING QUOTATION (GEMINI)---")
    enquiry = state["enquiry_details"]
    # itinerary_from_ai = state["itinerary_text"] # REMOVED
    
    parsed_vendor_info_dict = state.get("parsed_vendor_info", {})
    # This now contains the itinerary, price, inclusions, exclusions as extracted by the previous node
    vendor_extracted_details = parsed_vendor_info_dict.get("full_details_from_vendor", "Vendor details not available or parsing failed.")

    try:
        llm = get_llm_instance()
        # MODIFIED PROMPT: Itinerary now comes from vendor_extracted_details
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
        print(f"Error formatting final quotation with LLM (Gemini): {e}")
        return {"final_quotation": f"Error generating final quotation. Detail: {e}"}

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

def run_quotation_generation_graph(enquiry_details: dict, vendor_reply_text: str) -> str: # itinerary_text REMOVED
    initial_state = {
        "enquiry_details": enquiry_details,
        # "itinerary_text": itinerary_text, # REMOVED
        "vendor_reply_text": vendor_reply_text,
        "parsed_vendor_info": {},
        "final_quotation": ""
    }
    try:
        final_state = quotation_generation_graph.invoke(initial_state)
        return final_state.get("final_quotation", "Error: Quotation not generated (Gemini).")
    except Exception as e:
        print(f"Error running quotation graph (Gemini): {e}")
        return f"Critical error in quotation generation graph (Gemini): {e}"