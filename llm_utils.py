# llm_utils.py
import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List

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
        print(f"Error generating place suggestions with LLM ({provider}): {e}")
        return f"Error: Could not generate place suggestions using {provider}. Detail: {e}"

# --- PDF Generation Helper Class ---
class PDFQuotation(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self.set_left_margin(15)
        self.set_right_margin(15)
        
        # Attempt to add DejaVu fonts
        # IMPORTANT: User must place DejaVuSansCondensed.ttf and DejaVuSansCondensed-Bold.ttf
        # in an 'assets/fonts/' directory relative to this script.
        font_regular_path = os.path.join('assets', 'fonts', 'DejaVuSansCondensed.ttf')
        font_bold_path = os.path.join('assets', 'fonts', 'DejaVuSansCondensed-Bold.ttf')
        font_italic_path = os.path.join('assets', 'fonts', 'DejaVuSansCondensed-Oblique.ttf')

        try:
            if os.path.exists(font_regular_path):
                self.add_font('DejaVu', '', font_regular_path, uni=True)
            else:
                print(f"Warning: Font file not found: {font_regular_path}. Using Helvetica.")
                self.set_font('Helvetica', '', 10)

            if os.path.exists(font_bold_path):
                self.add_font('DejaVu', 'B', font_bold_path, uni=True)
            else:
                print(f"Warning: Font file not found: {font_bold_path}. Using Helvetica-Bold.")
                self.set_font('Helvetica', 'B', 10)

            if os.path.exists(font_italic_path):
                self.add_font('DejaVu', 'I', font_italic_path, uni=True)
            else:
                print(f"Warning: Font file not found: {font_italic_path}. Using Helvetica-Oblique.")
                self.set_font('Helvetica', 'I', 10)
        except RuntimeError as e:
            print(f"FPDF Error adding font (ensure font files are valid TTF and FreeType lib is installed): {e}")
            print("Falling back to Helvetica for DejaVu.")
            self.set_font('Helvetica', '', 10)
            self.set_font('Helvetica', 'B', 10)
            self.set_font('Helvetica', 'I', 10)

        # Determine available font family for later use
        self.font_family_available = {
            'regular': os.path.exists(font_regular_path),
            'bold': os.path.exists(font_bold_path),
            'italic': os.path.exists(font_italic_path)
        }
        self.set_font("DejaVu" if self.font_family_available['regular'] else "Helvetica", size=10)
        
        self.primary_color = (65, 125, 220) 
        self.text_color_dark = (50, 50, 50)
        self.text_color_light = (100, 100, 100)
        self.line_color = (220, 220, 220)
        self.highlight_bg_color = (255, 242, 204) 

        self.ICON_DESTINATION = "📍" if self._font_supports("📍") else "[Dest]"
        self.ICON_DURATION = "⏳" if self._font_supports("⏳") else "[Dur]"
        self.ICON_DATES = "🗓️" if self._font_supports("🗓️") else "[Date]"
        self.ICON_MEALPLAN = "🍽️" if self._font_supports("🍽️") else "[Meal]"
        self.ICON_VEHICLE = "🚗" if self._font_supports("🚗") else "[Veh]"
        self.ICON_GLOBE = "🌍" if self._font_supports("🌍") else "[Globe]"
        self.ICON_CHECKMARK = "✔️" if self._font_supports("✔️") else "[OK]"
        self.ICON_ARROW_RIGHT = "➡️" if self._font_supports("➡️") else ">"
        self.ICON_CROSS = "❌" if self._font_supports("❌") else "[X]"
        self.ICON_WARNING = "⚠️" if self._font_supports("⚠️") else "[!]"
        self.ICON_PHONE = "📞" if self._font_supports("📞") else "[Tel]"
        self.ICON_COLLABORATION = "🤝" if self._font_supports("🤝") else "[Co]"
        self.ICON_LINK = "🔗" if self._font_supports("🔗") else "[Link]"
        self.ICON_PACKAGE = "📦" if self._font_supports("📦") else "[Pkg]"
        self.ICON_SPARKLES = "✨" if self._font_supports("✨") else "*"  # Fallback for sparkles

    def _font_supports(self, char):
        # Simple stub: always return False (or True if you want to always use icons)
        # For robust implementation, check if the current font supports the character
        # but FPDF does not provide a direct way, so fallback to False for now
        return False

    def header_section_page1(self, data: Dict[str, Any]):
        banner_path = os.path.join("assets", "top_banner.png")
        if os.path.exists(banner_path):
            try:
                self.image(banner_path, x=0, y=0, w=self.w) 
            except RuntimeError as e: # Catch FPDF image errors (e.g., unsupported format)
                print(f"Error loading banner image {banner_path}: {e}. Skipping image.")
                self.ln(10)
        else:
            self.ln(10) 
            print(f"Warning: {banner_path} not found.")
        self.ln(60) 

        self.set_font("DejaVu", "B", 10)
        self.set_text_color(*self.text_color_dark)
        self.multi_cell(0, 5, f"{self.ICON_COLLABORATION} In collaboration with our trusted partners at TripExplore – crafting seamless travel experiences together.", align="C")
        self.ln(5)

        logo_rating_path = os.path.join("assets", "tripexplore-logo-with-rating.png")
        if os.path.exists(logo_rating_path):
            img_w = 80 
            img_h = 25 # Estimate, or get dynamically if PIL is used
            try:
                self.image(logo_rating_path, x=(self.w - img_w) / 2, y=self.get_y(), w=img_w) 
                self.ln(img_h + 5) 
            except RuntimeError as e:
                print(f"Error loading logo/rating image {logo_rating_path}: {e}. Skipping image.")
                self.ln(20)
        else:
            self.ln(20) 
            print(f"Warning: {logo_rating_path} not found.")

        self.set_draw_color(*self.line_color)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(10)

        self.set_font("DejaVu", "I", 10) 
        self.set_text_color(*self.text_color_light)
        img_placeholder_text = data.get("main_image_placeholder_text", "{ Image Relevant to The Destination }")
        self.cell(0, 10, img_placeholder_text, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        self.set_font("DejaVu", "B", 12)
        self.set_text_color(*self.primary_color)
        client_name = data.get("client_name", "Valued Client")
        self.cell(0, 10, f"{self.ICON_SPARKLES} Quotation for Tour Package – {client_name} {self.ICON_SPARKLES}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        
        details = [
            (self.ICON_DESTINATION + " Destination:", data.get("destination_summary", "N/A")),
            (self.ICON_DURATION + " Duration:", data.get("duration_summary", "N/A")),
            (self.ICON_DATES + " Dates:", data.get("dates_summary", "N/A")),
            (self.ICON_MEALPLAN + " Meal Plan:", data.get("meal_plan_summary", "N/A")),
            (self.ICON_VEHICLE + " Vehicle:", data.get("vehicle_summary", "N/A")),
        ]
        self.set_font("DejaVu", size=10)
        self.set_text_color(*self.text_color_dark)
        
        for label, value in details:
            self.set_font("DejaVu", "B")
            label_w = self.get_string_width(label + "  ") + 2 
            self.cell(label_w, 6, label)
            self.set_font("DejaVu", "")
            self.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT") 
            self.ln(1)

    def itinerary_section(self, data: Dict[str, Any]):
        self.add_page()
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*self.primary_color)
        self.cell(0, 10, "Itinerary to be followed", align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*self.text_color_dark)
        self.cell(0, 6, f"{self.ICON_PACKAGE} {data.get('destination_summary', '')} Package", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        
        hotel_details = data.get("hotel_details", [])
        if hotel_details:
            self.set_font("DejaVu", "B", 10)
            self.set_fill_color(*self.primary_color)
            self.set_text_color(255,255,255)
            col_w = (self.w - self.l_margin - self.r_margin) / 3
            self.cell(col_w, 7, "Destination/City", border=1, fill=True, align='C')
            self.cell(col_w, 7, "Hotel", border=1, fill=True, align='C')
            self.cell(col_w, 7, "Nights", border=1, fill=True, align='C', new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*self.text_color_dark)
            self.set_font("DejaVu", "", 9)
            for hotel in hotel_details:
                self.cell(col_w, 6, str(hotel.get("destination_location", "N/A")), border=1)
                self.cell(col_w, 6, str(hotel.get("hotel_name", "N/A")), border=1)
                self.cell(col_w, 6, str(hotel.get("nights", "N/A")), border=1, new_x="LMARGIN", new_y="NEXT") 
        self.ln(5)

        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*self.text_color_dark)
        self.cell(0, 8, data.get("itinerary_title", "Proposed Itinerary"), new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "", 9)
        detailed_itinerary = data.get("detailed_itinerary", [])
        for item in detailed_itinerary:
            day_num = str(item.get("day_number", "")) # Ensure string
            title = str(item.get("title", item.get("segment_title", ""))) # Ensure string
            desc = str(item.get("description", "")) # Ensure string
            self.set_font("DejaVu", "B", 10)
            if day_num:
                self.multi_cell(0, 6, f"{day_num}: {title}", new_x="LMARGIN", new_y="NEXT")
            else:
                self.multi_cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
            self.set_font("DejaVu", "", 9)
            self.set_text_color(*self.text_color_light)
            self.multi_cell(0, 5, desc, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*self.text_color_dark)
            self.ln(2)
        self.ln(5)

    def costs_inclusions_exclusions_section(self, data: Dict[str, Any]):
        self.set_font("DejaVu", "B", 10)
        self.set_text_color(*self.text_color_dark)
        
        self.multi_cell(0, 6, f"{self.ICON_CHECKMARK} Meals Included: (As per detailed itinerary / meal plan summary)", new_x="LMARGIN", new_y="NEXT")
        self.multi_cell(0, 6, f"{self.ICON_CHECKMARK} Double Sharing Room Required: (Assumed unless specified otherwise)", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        
        self.multi_cell(0, 6, f"Package Cost per Head: {data.get('cost_per_head', 'N/A')} {data.get('currency', '')}", new_x="LMARGIN", new_y="NEXT")
        pax = data.get('total_pax_for_cost', 'N/A')
        total_cost = data.get('total_package_cost', 'N/A')
        self.multi_cell(0, 6, f"Total Cost for {pax} PAX: {total_cost} {data.get('currency', '')} /-", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        gst_note = data.get("gst_note", "GST is additional and subject to RBI Regulations.")
        self.set_fill_color(*self.highlight_bg_color)
        self.set_font("DejaVu", "B", 9)
        self.multi_cell(0, 5, f"● {gst_note}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "B", 10) 
        self.ln(5)

        self.set_text_color(*self.primary_color)
        self.cell(0, 8, "Tour Cost Includes", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*self.text_color_dark)
        self.set_font("DejaVu", "", 9)
        inclusions = data.get("inclusions", [])
        for item in inclusions:
            self.multi_cell(0, 5, f"{self.ICON_ARROW_RIGHT} {str(item)}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.set_text_color(*self.primary_color)
        self.set_font("DejaVu", "B", 10)
        self.cell(0, 8, "Tour Cost Excludes", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*self.text_color_dark)
        self.set_font("DejaVu", "", 9)
        exclusions = data.get("exclusions", [])
        standard_exclusions = data.get("standard_exclusions_list", [])
        
        for item in exclusions: 
            self.multi_cell(0, 5, f"{self.ICON_CROSS} {str(item)}", new_x="LMARGIN", new_y="NEXT")
        for item in standard_exclusions: 
            self.multi_cell(0, 5, f"{self.ICON_ARROW_RIGHT} {str(item)}", new_x="LMARGIN", new_y="NEXT")
        
        self.ln(2)
        self.set_fill_color(*self.highlight_bg_color)
        self.set_font("DejaVu", "B", 9)
        self.multi_cell(0, 5, f"● {gst_note}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def final_notes_and_contact_section(self, data: Dict[str, Any]):
        if self.get_y() > self.h - 120 : 
             self.add_page()

        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*self.text_color_dark)
        self.multi_cell(0, 6, f"{self.ICON_WARNING} Important Note", new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "", 9)
        important_notes = data.get("important_notes", ["All services are subject to availability.", "Prices may vary based on final confirmation."])
        for note in important_notes:
            self.multi_cell(0, 5, f"- {str(note)}", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        
        self.set_font("DejaVu", "", 10)
        self.multi_cell(0,5, f"{self.ICON_PHONE} For further details or booking confirmation, feel free to contact us.", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font("DejaVu", "B", 10)
        self.multi_cell(0,5, "Best Regards,", new_x="LMARGIN", new_y="NEXT")
        self.multi_cell(0,5, data.get("company_contact_person", "V.R.Viswanathan") + " | " + data.get("company_phone", "+91-8884016046"), new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        self.set_text_color(*self.primary_color)
        self.set_font("DejaVu", "U", 10) 
        self.multi_cell(0,5, f"Click to Call : {data.get('company_phone', '')}", new_x="LMARGIN", new_y="NEXT", link=f"tel:{data.get('company_phone', '')}")
        clean_phone = str(data.get('company_phone', '')).replace('+', '').replace('-', '').replace(' ', '')
        self.multi_cell(0,5, "Click to Message Us on WhatsApp", new_x="LMARGIN", new_y="NEXT", link=f"https://wa.me/{clean_phone}")
        self.set_text_color(*self.text_color_dark) 
        self.set_font("DejaVu", "", 10) 
        self.ln(5)

        self.multi_cell(0, 5, f"{self.ICON_COLLABORATION} In collaboration with our trusted partners at TripExplore – crafting seamless travel experiences together.", align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.multi_cell(0,5, f"{self.ICON_LINK} Know more about them at: {data.get('company_website', 'www.tripexplore.in')}", new_x="LMARGIN", new_y="NEXT", link=data.get('company_website', ''))
        self.ln(5)

        self.set_font("DejaVu", "B", 11)
        self.multi_cell(0, 8, "TCS rules", new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "", 8)
        self.multi_cell(0, 4.5, data.get("tcs_rules_full", "TCS information not available."), new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

        logo_rating_path_footer = os.path.join("assets", "tripexplore-logo-with-rating.png")
        if os.path.exists(logo_rating_path_footer):
            img_w_footer = 70
            try:
                self.image(logo_rating_path_footer, x=(self.w - img_w_footer) / 2, y=self.get_y(), w=img_w_footer)
                self.ln(20) 
            except RuntimeError as e:
                print(f"Error loading footer logo/rating image {logo_rating_path_footer}: {e}. Skipping image.")
                self.ln(15)
        else:
            self.ln(15)
            print(f"Warning: Footer logo {logo_rating_path_footer} not found.")

# --- PDF Creation Function ---
def create_pdf_quotation_bytes(data: Dict[str, Any]) -> bytes:
    print("[PDF DEBUG] Starting PDF generation. Input data:", data)
    pdf = PDFQuotation(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    try:
        print("[PDF DEBUG] Rendering header_section_page1...")
        pdf.header_section_page1(data)
        print("[PDF DEBUG] Rendering itinerary_section...")
        pdf.itinerary_section(data)
        print("[PDF DEBUG] Rendering costs_inclusions_exclusions_section...")
        pdf.costs_inclusions_exclusions_section(data)
        print("[PDF DEBUG] Rendering final_notes_and_contact_section...")
        pdf.final_notes_and_contact_section(data)
        print("[PDF DEBUG] PDF generation complete. Returning bytes.")
        return bytes(pdf.output(dest='S'))
    except Exception as e:
        print(f"[PDF DEBUG] Exception during PDF generation: {e}")
        raise

    return bytes(pdf.output(dest='S')) 

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
Combine the Client Enquiry Details and the Parsed Vendor Information into a single, structured JSON object.
Strictly adhere to the JSON format and all specified keys. Ensure all string values are properly escaped for JSON.
The "detailed_itinerary" should be a list of objects, each with "day_number" (string), "title" (string), and "description" (string).
The "hotel_details" should be a list of objects, each with "destination_location" (string), "hotel_name" (string), and "nights" (string or number).
"inclusions" and "exclusions" should be lists of strings.

Client Enquiry Details:
- Destination: {destination}
- Number of Days: {num_days}
- Traveler Count: {traveler_count}
- Trip Type: {trip_type}
- Client Name (if available, use "Mr./Ms. [Client Name]", else "Mr./Ms. Valued Client"): {client_name_placeholder}

Parsed Vendor Information:
---
{vendor_parsed_text}
---

**Output JSON Structure (fill all keys, use "Not specified", default values, or empty lists [] if info is unavailable from vendor text):**
```json
{{
  "client_name": "{client_name_placeholder}",
  "quotation_title": "Tour Package for {destination}",
  "destination_summary": "{destination}",
  "duration_summary": "{num_days} Days / {num_nights} Nights", 
  "dates_summary": "Flexible / To be confirmed",
  "meal_plan_summary": "Refer to itinerary details or vendor inclusions",
  "vehicle_summary": "Private AC Vehicle as per itinerary or vendor inclusions",
  "main_image_placeholder_text": "Image representing {destination}",
  
  "itinerary_title": "Proposed Itinerary for your {trip_type} to {destination}",
  "detailed_itinerary": [ 
    {{ "day_number": "Day 1", "title": "Arrival in {destination} & Transfer to Hotel", "description": "Upon arrival at {destination} airport/station, meet our representative and transfer to your pre-booked hotel. Check-in and relax. Evening free for leisure or explore nearby areas. Overnight stay in {destination}."}}
  ],
  "hotel_details": [
    {{ "destination_location": "{destination}", "hotel_name": "Standard Category Hotel (or similar)", "nights": "{num_nights}" }}
  ],

  "cost_per_head": "Not specified", 
  "total_pax_for_cost": "{traveler_count}",
  "total_package_cost": "Not specified",
  "currency": "INR", 

  "inclusions": ["Accommodation in specified hotels", "Meals as per itinerary (e.g., Breakfast)", "Transfers and sightseeing by AC vehicle", "All applicable hotel taxes"],
  "exclusions": ["Airfare/Train fare", "Visa fees", "Early check-in/late check-out charges", "Personal expenses", "Anything not mentioned in inclusions"],
  
  "gst_note": "GST is additional at 5% and is subject to RBI Regulations.",
  "tcs_note_short": "TCS as per government regulations will be applicable for overseas packages.",
  
  "company_contact_person": "V.R.Viswanathan",
  "company_phone": "+91-8884016046",
  "company_email": "vrtravelpackages@gmail.com",
  "company_website": "www.tripexplore.in",

  "standard_exclusions_list": [
        "5% TCS will be returned to your PAN and can be claimed while filing Income Tax (for applicable overseas packages).",
        "Meals other than those specified are not included.",
        "Additional facility usage at the hotel is chargeable.",
        "Tips are not mandatory.",
        "Travel insurance is not mandatory (but highly recommended)."
  ],
  "important_notes": [
      "All services are subject to availability at the time of booking.",
      "Rates may change if travel dates, number of pax, or hotels change.",
      "This quotation is valid for 7 days from the date of issue, unless specified otherwise."
  ],
  "tcs_rules_full": "Note: Effective 01 October 2023, 'Tax Collected at Source' (TCS), will be at 5% till Rs. 7 lakh, and 20% thereafter, for all Cumulative Payments made against a PAN in the Current Financial Year. The Buyer will have to Furnish an Undertaking on their spends for Overseas Tour Packages/ Cruises in the year. The Government of India, Ministry of Finance, via Circular No. 10 of 2023, F. No. 37 014212312023-TPL, dated 30th June, 2023, has clarified that the information is to be furnished by the buyer in an undertaking and any false information will merit appropriate action against the buyer under the Finance Act, 2023 amended sub-section (1G) of section 206C of the income-tax Act, 1961."
}}

"""
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


    def _font_supports(self, char):
        try:
            # Try to get the width of the character; if 0, font likely doesn't support it
            width = self.get_string_width(char)
            return width > 0.5
        except Exception:
            return False
