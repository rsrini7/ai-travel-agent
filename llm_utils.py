# llm_utils.py
import os
from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI # Removed
from langchain_google_genai import ChatGoogleGenerativeAI # Added
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Removed
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Added

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

# Initialize LLM with Gemini
# Use "gemini-1.5-flash-latest" for the fast model.
# If a specific "Gemini 2.0 Flash" model ID becomes available, update here.
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    google_api_key=GOOGLE_API_KEY,
    # Optional: add safety_settings if needed, e.g.,
    # safety_settings={
    #     HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    #     HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    # },
    convert_system_message_to_human=True # Gemini API typically prefers system instructions as part of the first human message or specific structures.
                                         # This can help adapt existing prompts.
)


def generate_itinerary_llm(enquiry_details: dict) -> str:
    """
    Generates a basic itinerary using Langchain with Gemini.
    enquiry_details: dict like {'destination': 'Paris', 'num_days': 3, 'traveler_count': 2, 'trip_type': 'Leisure'}
    """
    # Gemini might respond better if system-like instructions are part of the human message
    # or if we avoid a separate "system" message if convert_system_message_to_human=False.
    # For convert_system_message_to_human=True, this structure is fine.
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful travel assistant. Generate a concise day-by-day itinerary."),
        ("human", "Generate a {num_days}-day itinerary for {traveler_count} traveler(s) visiting {destination} for a {trip_type} trip. Focus on major attractions and suggest a balanced pace. Provide output as a simple text, day by day.")
    ])
    output_parser = StrOutputParser()
    chain = prompt_template | llm | output_parser
    
    try:
        response = chain.invoke(enquiry_details)
        return response
    except Exception as e:
        print(f"Error generating itinerary with LLM (Gemini): {e}")
        # You might want to check for specific Gemini API errors here
        return f"Error: Could not generate itinerary. Detail: {e}"

# --- LangGraph for Quotation Generation ---

class QuotationState(TypedDict):
    enquiry_details: dict
    itinerary_text: str
    vendor_reply_text: str
    parsed_vendor_info: Annotated[dict, operator.add]
    final_quotation: str

def fetch_data_node(state: QuotationState):
    print("---FETCHING DATA (Simulated, data passed in initial state)---")
    return {
        "enquiry_details": state["enquiry_details"],
        "itinerary_text": state["itinerary_text"],
        "vendor_reply_text": state["vendor_reply_text"]
    }

def parse_vendor_reply_node(state: QuotationState):
    print("---PARSING VENDOR REPLY (GEMINI)---")
    vendor_reply = state["vendor_reply_text"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at parsing vendor replies for travel quotations. Extract key information like total price, inclusions (list them), and exclusions (list them). If not found, state 'Not specified'. Output in a simple key: value format or a short summary."),
        ("human", "Parse the following vendor reply and extract total price, inclusions, and exclusions:\n\n{vendor_reply}")
    ])
    parser = StrOutputParser()
    chain = prompt | llm | parser
    
    try:
        parsed_info_str = chain.invoke({"vendor_reply": vendor_reply})
        return {"parsed_vendor_info": {"summary": parsed_info_str}}
    except Exception as e:
        print(f"Error parsing vendor reply with LLM (Gemini): {e}")
        return {"parsed_vendor_info": {"summary": f"Error parsing vendor reply. Detail: {e}"}}


def combine_and_format_node(state: QuotationState):
    print("---COMBINING AND FORMATTING QUOTATION (GEMINI)---")
    enquiry = state["enquiry_details"]
    itinerary = state["itinerary_text"]
    parsed_vendor_info = state["parsed_vendor_info"].get("summary", "Vendor details not available.")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel agent creating a client quotation. Combine the itinerary and vendor information into a professional, clean, and structured quotation. Start with a greeting, include trip details, the day-wise itinerary, vendor pricing/inclusions, and a closing remark."),
        ("human", """
        Create a quotation based on the following:
        Enquiry Details:
        - Destination: {destination}
        - Number of Days: {num_days}
        - Traveler Count: {traveler_count}
        - Trip Type: {trip_type}

        Proposed Itinerary:
        ---
        {itinerary}
        ---

        Vendor Information (Pricing, Inclusions/Exclusions):
        ---
        {vendor_info}
        ---
        
        Format it clearly.
        """)
    ])
    parser = StrOutputParser()
    chain = prompt | llm | parser

    try:
        final_quotation_text = chain.invoke({
            "destination": enquiry.get("destination", "N/A"),
            "num_days": enquiry.get("num_days", "N/A"),
            "traveler_count": enquiry.get("traveler_count", "N/A"),
            "trip_type": enquiry.get("trip_type", "N/A"),
            "itinerary": itinerary,
            "vendor_info": parsed_vendor_info
        })
        return {"final_quotation": final_quotation_text}
    except Exception as e:
        print(f"Error formatting final quotation with LLM (Gemini): {e}")
        return {"final_quotation": f"Error generating final quotation. Detail: {e}"}

# Define the graph (remains the same)
workflow = StateGraph(QuotationState)

workflow.add_node("fetch_data", fetch_data_node)
workflow.add_node("parse_vendor", parse_vendor_reply_node)
workflow.add_node("format_quotation", combine_and_format_node)

workflow.set_entry_point("fetch_data")
workflow.add_edge("fetch_data", "parse_vendor")
workflow.add_edge("parse_vendor", "format_quotation")
workflow.add_edge("format_quotation", END)

quotation_generation_graph = workflow.compile()

def run_quotation_generation_graph(enquiry_details: dict, itinerary_text: str, vendor_reply_text: str) -> str:
    initial_state = {
        "enquiry_details": enquiry_details,
        "itinerary_text": itinerary_text,
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