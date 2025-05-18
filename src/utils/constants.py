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
