from dotenv import load_dotenv

# Load .env file at the very beginning
load_dotenv()

import streamlit as st
from src.models import AppSessionState

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