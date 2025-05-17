# llm_utils.py
import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any
from pdf_utils import create_pdf_quotation_bytes

from fpdf import FPDF # Import FPDF

load_dotenv()

# --- LLM Instance Utility ---
def get_llm_instance(provider: str):
    """
    Returns an LLM instance based on the specified provider.
    """
    if provider == "Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Gemini. Check .env file and ensure it's loaded.")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key)
    elif provider == "OpenRouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model_name = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5") 
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found for OpenRouter. Check .env file and ensure it's loaded.")
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000") 
        app_title = os.getenv("OPENROUTER_APP_TITLE", "AI Travel Quotation") 
        headers = {"HTTP-Referer": http_referer, "X-Title": app_title}
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key, 
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}. Supported providers are 'Gemini', 'OpenRouter'.")

# --- Places Suggestion Function ---
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
        error_msg = f"Error generating place suggestions with LLM ({provider}): {e}"
        print(error_msg)
        if provider == "OpenRouter" and hasattr(e, 'response') and hasattr(e.response, 'json'):
            error_data = e.response.json()
            if 'error' in error_data and 'message' in error_data['error']:
                return f"OpenRouter Model Error: {error_data['error']['message']}"
        return f"Error: Could not generate place suggestions using {provider}. Detail: {str(e)}"

# --- LangGraph State and Nodes ---
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
        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are an expert at parsing vendor replies for travel quotations. 
From the vendor reply provided below, extract the following information clearly:
1.  **Proposed Itinerary:** (Day-by-day plan or tour flow. If none, state 'Itinerary not specified by vendor.')
2.  **Hotel Details:** (List any mentioned hotels, their category, and for which city/duration if specified. If none, state 'Hotel details not specified by vendor'.)
3.  **Total Price or Per Person Price:** (e.g., USD 1200 per person, INR 50000 total for 2 pax. If not found, state 'Price not specified'.)
4.  **Currency:** (e.g., USD, INR. If not found, state 'Currency not specified'.)
5.  **Number of Pax cost is based on:** (e.g., "for 2 adults", "per person". If not clear, state 'Not specified'.)
6.  **Inclusions:** (List them. If not found, state 'Inclusions not specified'.)
7.  **Exclusions:** (List them. If not found, state 'Exclusions not specified'.)

Vendor Reply:
---
{vendor_reply}
---

Enquiry Context (for your reference):
- Destination: {destination}
- Duration: {num_days} days

Output the extracted information clearly under respective headings.""")
        ])
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
        return {"parsed_vendor_info_text": f"Error parsing vendor reply using {provider}. Detail: {e}"}

def structure_data_for_pdf_node(state: QuotationGenerationState):
    enquiry = state["enquiry_details"]
    vendor_parsed_text = state["parsed_vendor_info_text"]
    provider = state["ai_provider"]

    json_prompt_template = """
You are a travel agent assistant preparing data for a PDF quotation document.
Your goal is to transform the Client Enquiry Details and the Parsed Vendor Information into a single, structured JSON object.
Strictly adhere to the JSON format and all specified keys. Ensure all string values are properly escaped for JSON.

**Information Sources:**
1.  **Client Enquiry Details:** Basic trip requirements.
2.  **Parsed Vendor Information:** This is output from a previous step where a vendor's textual reply was processed. It *should* contain specific details like proposed itinerary, hotel details, pricing, meals included, room configuration, inclusions, and exclusions provided by the vendor.

**Crucial Task: Detailed Itinerary Generation**
- You MUST generate a comprehensive, engaging, day-wise itinerary for the full duration of `{num_days}` days.
- Source information primarily from the "Proposed Itinerary" section of the "Parsed Vendor Information."
- **Structure each day** within the "detailed_itinerary" list as an object containing:
    - "day_number": (String, e.g., "Day 1", "Day 2")
    - "title": (String, a concise and appealing headline for the day's activities, e.g., "Arrival in Paris & Eiffel Tower Magic", "Exploring Ancient Rome: Colosseum & Forum")
    - "description": (String, a well-written paragraph or two detailing the day's activities, sightseeing, meals if specified, and flow. Use descriptive language to make it sound attractive to the client.)
- **Completeness:**
    - If the vendor's itinerary is detailed and covers all `{num_days}` days, adapt it to the structure above, enhancing descriptions where possible.
    - If the vendor's itinerary is brief, missing days, or not strictly day-wise:
        - You MUST expand upon it logically to cover all `{num_days}` days.
        - For any missing days, creatively and plausibly generate activities based on the destination (`{destination}`), trip type (`{trip_type}`), and common tourist interests for such a trip. Make it sound like a coherent and well-planned experience.
        - Ensure a smooth flow between days.
- **If the vendor reply provides NO itinerary details at all (check "Proposed Itinerary" in Parsed Vendor Information):**
    - You MUST create a compelling, generic, day-wise itinerary for `{num_days}` days in `{destination}` suitable for a `{trip_type}` trip.
    - In the description of "Day 1" for such a generated itinerary, include a note like: "(Please note: This is a suggested itinerary based on popular activities. We can customize it further to your preferences.)"
- **Beautification & Clarity:**
    - Use clear, professional, and engaging language throughout the itinerary descriptions.
    - Avoid jargon. Highlight key experiences.
    - Ensure correct grammar and spelling.

**Populating JSON Fields from Parsed Vendor Information:**
- **`meal_plan_summary`**: Extract this from the "Meals Included" section of the `Parsed Vendor Information`. If not specified there, use a sensible default like "Daily breakfast at hotel; other meals as per detailed itinerary".
- **`room_configuration_summary`**: Extract this from the "Rooms Required/Configuration" section of the `Parsed Vendor Information`. If not specified there, use "Standard double occupancy rooms (or as per final booking confirmation)".
- **`cost_per_head`, `total_package_cost`, `currency`**: Extract these from the "Total Price or Per Person Price" and "Currency" sections of `Parsed Vendor Information`. If not found, use defaults like "To be advised" or "INR".
- **`inclusions`, `exclusions`**: Primarily use the "Inclusions" and "Exclusions" lists from `Parsed Vendor Information`. If these are minimal or missing, you can augment them with the standard items provided in the JSON template below, but vendor-provided specifics take precedence.
- **`hotel_details`**: Use information from "Hotel Details" in `Parsed Vendor Information`. If none, use the template's default.

Client Enquiry Details:
- Destination: {destination}
- Number of Days: {num_days}
- Traveler Count: {traveler_count}
- Trip Type: {trip_type}
- Client Name (if available, use "Mr./Ms. [Client Name]", else "Mr./Ms. Valued Client"): {client_name_placeholder}

Parsed Vendor Information (This contains what the vendor provided, including their proposed itinerary, meals, room configuration, pricing, etc.):
---
{vendor_parsed_text}
---

**Output JSON Structure (fill all keys, using information as per instructions above. Use "Not specified", default values, or empty lists [] if info is unavailable and cannot be plausibly generated/derived for non-itinerary fields):**
```json
{{
  "client_name": "{client_name_placeholder}",
  "quotation_title": "Your Exclusive Travel Package to {destination}",
  "destination_summary": "{destination}",
  "duration_summary": "{num_days} Days / {num_nights} Nights of Adventure & Discovery",
  "dates_summary": "Flexible Travel Dates (To be finalized)",
  "meal_plan_summary": "Daily breakfast at hotel; other meals as per detailed itinerary",
  "room_configuration_summary": "Standard double occupancy rooms (or as per final booking confirmation)",
  "vehicle_summary": "Comfortable Private AC Vehicle for all transfers and sightseeing as per itinerary",
  "main_image_placeholder_text": "A Glimpse of {destination}'s Charm",
  
  "itinerary_title": "Your Personalized {num_days}-Day Journey in {destination}",
  "detailed_itinerary": [ 
    // Example for ONE day. Generate for ALL {num_days} days following the detailed instructions above.
    {{ 
      "day_number": "Day 1", 
      "title": "Arrival in {destination} & Evening at Leisure", 
      "description": "Welcome to the vibrant city of {destination}! Upon your arrival at the international airport/railway station, our friendly representative will greet you and assist with a smooth transfer to your pre-booked hotel. Complete your check-in formalities and take some time to relax and settle in. The rest of the evening is yours to explore the nearby surroundings at your own pace, perhaps indulging in some local snacks or simply soaking in the new atmosphere. Enjoy a comfortable overnight stay at your hotel in {destination}."
    }} 
    // ... more day objects up to Day {num_days} ...
  ],
  "hotel_details": [
    {{ "destination_location": "{destination}", "hotel_name": "Selected 3-Star/4-Star Hotel (or similar, based on package)", "nights": "{num_nights}" }}
  ],

  "cost_per_head": "To be advised based on final customization", 
  "total_pax_for_cost": "{traveler_count}",
  "total_package_cost": "Please refer to final proposal",
  "currency": "INR", 

  "inclusions": [
      "Accommodation as per room configuration summary in specified category hotels.",
      "Meals as per the meal plan summary.",
      "All transfers, sightseeing, and inter-city travel by a private air-conditioned vehicle.",
      "Driver's allowance, fuel charges, parking fees, and toll taxes.",
      "All applicable hotel and transport taxes."
    ],
  "exclusions": [
      "International or domestic airfare/train fare unless specified.",
      "Visa charges, travel insurance.",
      "Any meals other than those mentioned in the 'Meals Included' or itinerary.",
      "Entrance fees to monuments, museums, parks, and attractions.",
      "Personal expenses such as laundry, telephone calls, tips, porterage, etc.",
      "Any services not explicitly mentioned in the 'Inclusions' section."
    ],
  
  "gst_note": "GST (Goods and Services Tax) will be applicable as per government norms, currently 5% on tour packages.",
  "tcs_note_short": "TCS may be applicable for overseas packages as per prevailing government regulations.",
  
  "company_contact_person": "V.R.Viswanathan",
  "company_phone": "+91-8884016046",
  "company_email": "vrtravelpackages@gmail.com",
  "company_website": "www.tripexplore.in",

  "standard_exclusions_list": [
        "Expenses of personal nature like tips, laundry, phone calls, alcoholic beverages etc.",
        "Any increase in airfare, visa fees, or taxes levied by the government.",
        "Cost of any optional tours, activities, or services.",
        "Early check-in & late check-out charges at hotels (standard check-in/out times apply)."
  ],
  "important_notes": [
      "This is a proposed itinerary and is subject to change/customization based on your preferences and availability.",
      "All hotel accommodations are subject to availability at the time of booking. In case of unavailability, similar category hotels will be provided.",
      "Rates are valid for the period mentioned and for Indian nationals only, unless specified otherwise.",
      "Standard check-in time at hotels is 14:00 hrs and check-out is 12:00 hrs."
  ],
  "tcs_rules_full": "Note: Effective 01 October 2023, 'Tax Collected at Source' (TCS), will be at 5% till Rs. 7 lakh, and 20% thereafter, for all Cumulative Payments made against a PAN in the Current Financial Year. The Buyer will have to Furnish an Undertaking on their spends for Overseas Tour Packages/ Cruises in the year. The Government of India, Ministry of Finance, via Circular No. 10 of 2023, F. No. 37 014212312023-TPL, dated 30th June, 2023, has clarified that the information is to be furnished by the buyer in an undertaking and any false information will merit appropriate action against the buyer under the Finance Act, 2023 amended sub-section (1G) of section 206C of the income-tax Act, 1961."
}}"""
    try:
        llm = get_llm_instance(provider)
        num_days_int = int(enquiry.get("num_days", 0))
        num_nights = num_days_int - 1 if num_days_int > 0 else 0

        prompt = ChatPromptTemplate.from_template(json_prompt_template)
        
        if provider == "OpenRouter" and ("gpt" in os.getenv("OPENROUTER_DEFAULT_MODEL", "").lower() or "claude-3" in os.getenv("OPENROUTER_DEFAULT_MODEL", "").lower()):
            llm_for_json = get_llm_instance(provider) 
            if not hasattr(llm_for_json, 'model_kwargs') or llm_for_json.model_kwargs is None:
                llm_for_json.model_kwargs = {}
            llm_for_json.model_kwargs["response_format"] = {"type": "json_object"}
            chain = prompt | llm_for_json | JsonOutputParser()
        elif provider == "Gemini": 
            updated_json_prompt = json_prompt_template.replace("```json", "Please provide your response strictly in the following JSON format, ensuring all strings are correctly escaped:\n```json")
            prompt = ChatPromptTemplate.from_template(updated_json_prompt)
            chain = prompt | llm | StrOutputParser() 
        else: 
            chain = prompt | llm | StrOutputParser()

        response_data = chain.invoke({
            "destination": enquiry.get("destination", "N/A"),
            "num_days": str(enquiry.get("num_days", "N/A")),
            "num_nights": str(num_nights),
            "traveler_count": str(enquiry.get("traveler_count", "N/A")),
            "trip_type": enquiry.get("trip_type", "N/A"),
            "client_name_placeholder": "Mr./Ms. Valued Client", 
            "vendor_parsed_text": vendor_parsed_text
        })

        if isinstance(response_data, str): 
            try:
                cleaned_response = response_data.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                structured_data = json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from LLM string output: {e}")
                print(f"LLM String Output was:\n{response_data}")
                return {"structured_quotation_data": {"error": "Failed to parse JSON from LLM", "raw_output": response_data}}
        elif isinstance(response_data, dict): 
            structured_data = response_data
        else:
            return {"structured_quotation_data": {"error": "Unexpected LLM output type for JSON."}}

        # Ensure all list items are strings for PDF generation robustness
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
        return {"structured_quotation_data": {"error": f"LLM error during JSON generation: {e}"}}

def generate_pdf_node(state: QuotationGenerationState):
    structured_data = state.get("structured_quotation_data")
    if not structured_data or "error" in structured_data:
        error_message = structured_data.get("error", "Unknown error before PDF generation")
        print(f"Skipping PDF generation due to previous error: {error_message}")
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 10, f"Error generating PDF: {error_message}\n\nLLM Raw Output (if any):\n{structured_data.get('raw_output', 'N/A')}")
        return {"pdf_output_bytes": pdf.output(dest='S')}
    try:
        pdf_bytes = create_pdf_quotation_bytes(structured_data)
        return {"pdf_output_bytes": pdf_bytes}
    except Exception as e:
        print(f"Critical error during PDF generation: {e}")
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 10, f"Critical error during PDF file creation: {e}")
        return {"pdf_output_bytes": pdf.output(dest='S')}

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

quotation_generation_graph_pdf = workflow.compile() # Compile once when module loads

def run_quotation_generation_graph(enquiry_details: dict, vendor_reply_text: str, provider: str) -> bytes:
    initial_state = QuotationGenerationState(
    enquiry_details=enquiry_details,
    vendor_reply_text=vendor_reply_text,
    parsed_vendor_info_text="",
    structured_quotation_data={},
    pdf_output_bytes=b"",
    ai_provider=provider
    )
    try:
        final_state = quotation_generation_graph_pdf.invoke(initial_state)
        pdf_bytes = final_state.get("pdf_output_bytes")
        if not pdf_bytes: # Should be handled by generate_pdf_node, but as a safeguard
            pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Error: PDF generation failed, no bytes returned from graph unexpectedly.")
            return pdf.output(dest='S')
        return pdf_bytes
    except Exception as e:
        print(f"Error running quotation graph ({provider}): {e}")
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0,10, f"Critical error in quotation generation graph ({provider}): {e}")
        return pdf.output(dest='S')
