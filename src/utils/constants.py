# src/utils/constants.py
import os

# --- Base Directory ---
# Get the directory of the current file (src/utils/constants.py)
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up two levels to get the project root (src/utils/ -> src/ -> project_root/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_FILE_DIR)) # This is the key change

# --- Asset Paths ---
# Assets directory is directly under PROJECT_ROOT
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# Font files
FONT_DEJAVU_REGULAR = os.path.join(FONTS_DIR, "DejaVuSansCondensed.ttf")
FONT_DEJAVU_BOLD = os.path.join(FONTS_DIR, "DejaVuSansCondensed-Bold.ttf")
FONT_DEJAVU_ITALIC = os.path.join(FONTS_DIR, "DejaVuSansCondensed-Oblique.ttf")

# Image files (ensure these names match your actual files in the assets folder)
IMAGE_TOP_BANNER = os.path.join(ASSETS_DIR, "top_banner.png")
IMAGE_TRIPEXPLORE_LOGO_RATING = os.path.join(ASSETS_DIR, "tripexplore-logo-with-rating.png")


# --- Supabase ---
# Table Names
TABLE_ENQUIRIES = "enquiries"
TABLE_CLIENTS = "clients"
TABLE_ITINERARIES = "itineraries"
TABLE_VENDOR_REPLIES = "vendor_replies"
TABLE_QUOTATIONS = "quotations"

# Storage Bucket Names
BUCKET_QUOTATIONS = "quotations"


# --- UI & Session State Keys (examples, can be expanded) ---
# SESSION_KEY_SELECTED_AI_PROVIDER = "selected_ai_provider"
# SESSION_KEY_SELECTED_MODEL_FOR_PROVIDER = "selected_model_for_provider"

# Tab 2
# SESSION_KEY_TAB2_SELECTED_ENQUIRY_ID = "selected_enquiry_id"
# SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS = "current_ai_suggestions"
# SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID = "current_ai_suggestions_id"
# SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG = "itinerary_loaded_for_tab2"

# Tab 3
# SESSION_KEY_TAB3_SELECTED_ENQUIRY_ID = "selected_enquiry_id_tab3"
# Add other tab3 specific session keys here if centralizing them is desired

# General
# SESSION_KEY_OPERATION_SUCCESS_MESSAGE = "operation_success_message"