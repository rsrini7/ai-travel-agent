from dotenv import load_dotenv

# Load .env file at the very beginning
load_dotenv()

import streamlit as st

# Import tab rendering functions
from src.ui.tabs.tab1_new_enquiry import render_tab1
from src.ui.tabs.tab2_manage_itinerary import render_tab2
from src.ui.tabs.tab3_vendor_quotation import render_tab3

# Import sidebar rendering function
from src.ui.sidebar import render_sidebar

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Agent Automation")

# --- Initialize session state variables - centralized here ---
if 'selected_ai_provider' not in st.session_state:
    st.session_state.selected_ai_provider = "OpenRouter" 
if 'selected_model_for_provider' not in st.session_state:
    st.session_state.selected_model_for_provider = None

# Tab 2 specific (using constants.SESSION_KEY_TAB2_... if desired, but direct keys are also fine here)
if 'selected_enquiry_id' not in st.session_state: # This is for tab2
    st.session_state.selected_enquiry_id = None
if 'current_ai_suggestions' not in st.session_state:
    st.session_state.current_ai_suggestions = None
if 'current_ai_suggestions_id' not in st.session_state:
    st.session_state.current_ai_suggestions_id = None
if 'itinerary_loaded_for_tab2' not in st.session_state:
    st.session_state.itinerary_loaded_for_tab2 = None

# Tab 3 specific states
if 'selected_enquiry_id_tab3' not in st.session_state: # This is for tab3
    st.session_state.selected_enquiry_id_tab3 = None
if 'tab3_enquiry_details' not in st.session_state:
    st.session_state.tab3_enquiry_details = None
if 'tab3_client_name' not in st.session_state:
    st.session_state.tab3_client_name = "Valued Client"
if 'tab3_itinerary_info' not in st.session_state:
    st.session_state.tab3_itinerary_info = None
if 'tab3_vendor_reply_info' not in st.session_state:
    st.session_state.tab3_vendor_reply_info = None

if 'tab3_current_quotation_db_id' not in st.session_state:
    st.session_state.tab3_current_quotation_db_id = None
if 'tab3_current_pdf_storage_path' not in st.session_state:
    st.session_state.tab3_current_pdf_storage_path = None
if 'tab3_current_docx_storage_path' not in st.session_state:
    st.session_state.tab3_current_docx_storage_path = None

if 'tab3_quotation_pdf_bytes' not in st.session_state:
    st.session_state.tab3_quotation_pdf_bytes = None
if 'tab3_quotation_docx_bytes' not in st.session_state:
    st.session_state.tab3_quotation_docx_bytes = None

if 'show_quotation_success_tab3' not in st.session_state:
    st.session_state.show_quotation_success_tab3 = False
if 'operation_success_message' not in st.session_state: 
    st.session_state.operation_success_message = None

if 'tab3_cached_graph_output' not in st.session_state:
    st.session_state.tab3_cached_graph_output = None
if 'tab3_cache_key' not in st.session_state:
    st.session_state.tab3_cache_key = None


# --- Render Sidebar ---
render_sidebar()

# --- Tab Definitions ---
tab1, tab2, tab3 = st.tabs([
    "📝 New Enquiry",
    "🔍 Manage Enquiries & Itinerary",
    "✍️ Add Vendor Reply & Generate Quotation"
])

with tab1:
    render_tab1()

with tab2:
    render_tab2()

with tab3:
    render_tab3()