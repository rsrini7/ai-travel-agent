from dotenv import load_dotenv

# Load .env file at the very beginning
load_dotenv()

import streamlit as st
from typing import Optional, Any, List, Dict # Ensure all necessary imports are present
from pydantic import BaseModel, Field

# Pydantic Model Definitions
class AIConfigState(BaseModel):
    selected_ai_provider: str = "OpenRouter"
    selected_model_for_provider: Optional[str] = None

class Tab2State(BaseModel):
    selected_enquiry_id: Optional[Any] = None
    current_ai_suggestions: Optional[Any] = None
    current_ai_suggestions_id: Optional[Any] = None
    itinerary_loaded_for_tab2: Optional[Any] = None

class Tab3State(BaseModel):
    selected_enquiry_id: Optional[Any] = None # Was selected_enquiry_id_tab3
    enquiry_details: Optional[Any] = None
    client_name: str = "Valued Client"
    itinerary_info: Optional[Any] = None
    vendor_reply_info: Optional[Any] = None
    current_quotation_db_id: Optional[Any] = None
    current_pdf_storage_path: Optional[str] = None
    current_docx_storage_path: Optional[str] = None
    quotation_pdf_bytes: Optional[bytes] = None
    quotation_docx_bytes: Optional[bytes] = None
    show_quotation_success: bool = False # Was show_quotation_success_tab3
    cached_graph_output: Optional[Any] = None
    cache_key: Optional[str] = None

class AppSessionState(BaseModel):
    ai_config: AIConfigState = Field(default_factory=AIConfigState)
    tab2_state: Tab2State = Field(default_factory=Tab2State)
    tab3_state: Tab3State = Field(default_factory=Tab3State)
    operation_success_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

# Import tab rendering functions
from src.ui.tabs.tab1_new_enquiry import render_tab1
from src.ui.tabs.tab2_manage_itinerary import render_tab2
from src.ui.tabs.tab3_vendor_quotation import render_tab3

# Import sidebar rendering function
from src.ui.sidebar import render_sidebar

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Agent Automation")

# --- Initialize session state ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = AppSessionState()


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