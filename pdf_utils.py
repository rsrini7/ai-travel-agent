# pdf_utils.py
from typing import Dict, Any
import os
from fpdf import FPDF


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

    def _font_supports(self, char): # char argument is not used by this simple check
        return self.font_family_available['regular'] # True if DejaVu regular was loaded

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
            img_w = 150 
            img_h = 50 # Estimate, or get dynamically if PIL is used
            try:
                self.image(logo_rating_path, x=(self.w - img_w) / 2, y=self.get_y(), w=img_w) 
                self.ln(img_h + 5) 
            except RuntimeError as e:
                print(f"Error loading logo/rating image {logo_rating_path}: {e}. Skipping image.")
                self.ln(20)
        else:
            self.ln(20) 
            print(f"Warning: {logo_rating_path} not found.")

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
        for item in standard_exclusions: # Changed Icon Here
            self.multi_cell(0, 5, f"{self.ICON_CROSS} {str(item)}", new_x="LMARGIN", new_y="NEXT")
        
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
    