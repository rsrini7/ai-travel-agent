# app.py
import os # Add os import if not already there
from dotenv import load_dotenv # Add dotenv import

# --- ADD THIS AT THE VERY TOP ---
# Explicitly load .env here before any other project imports that might need environment variables
# This ensures it's loaded as early as possible.
if load_dotenv():
    print("APP.PY: .env file loaded successfully by app.py's initial load_dotenv().")
else:
    print("APP.PY: .env file not found by app.py's initial load_dotenv().")
    
import streamlit as st
from supabase_utils import (
    add_enquiry, get_enquiries, get_enquiry_by_id,
    add_itinerary, get_itinerary_by_enquiry_id,
    add_vendor_reply, get_vendor_reply_by_enquiry_id,
    add_quotation, get_quotation_by_enquiry_id
)
from llm_utils import generate_itinerary_llm, run_quotation_generation_graph # Assuming llm_utils is correct

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Automation MVP")

# Initialize session state variables if they don't exist
if 'selected_enquiry_id' not in st.session_state:
    st.session_state.selected_enquiry_id = None
if 'current_itinerary' not in st.session_state:
    st.session_state.current_itinerary = None
if 'current_vendor_reply' not in st.session_state:
    st.session_state.current_vendor_reply = None
if 'current_quotation' not in st.session_state:
    st.session_state.current_quotation = None


# --- Tabs for different functionalities ---
tab1, tab2, tab3 = st.tabs(["📝 New Enquiry", "🔍 Manage Enquiries & Generate", "✍️ Add Vendor Reply"])

with tab1:
    st.header("1. Submit New Enquiry")
    with st.form("new_enquiry_form"):
        destination = st.text_input("Destination", placeholder="e.g., Paris, France")
        num_days = st.number_input("Number of Days", min_value=1, value=7)
        traveler_count = st.number_input("Number of Travelers", min_value=1, value=2)
        trip_type = st.selectbox("Trip Type", ["Leisure", "Business", "Adventure", "Honeymoon", "Family"])
        
        submitted_enquiry = st.form_submit_button("Submit Enquiry")
        if submitted_enquiry:
            if not destination:
                st.error("Destination is required.")
            else:
                with st.spinner("Submitting enquiry..."):
                    enquiry_data, error_msg = add_enquiry(destination, num_days, traveler_count, trip_type)
                    if enquiry_data:
                        st.success(f"Enquiry submitted successfully! ID: {enquiry_data['id']}")
                        st.session_state.selected_enquiry_id = enquiry_data['id'] 
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}") # CHANGED

with tab2:
    st.header("2. Manage Enquiries & Generate Documents")
    
    enquiries_list, error_msg = get_enquiries() # CHANGED
    if error_msg: # CHANGED
        st.error(f"Could not load enquiries: {error_msg}") # CHANGED
        enquiries_list = []

    if not enquiries_list:
        st.info("No enquiries found. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id = None
    else:
        enquiry_options = {f"{e['id'][:8]}... - {e['destination']} ({e['created_at'][:10]})": e['id'] for e in enquiries_list}
        
        # Handle initial selection better if selected_enquiry_id is not in current options
        current_selection_index = 0
        if st.session_state.selected_enquiry_id and st.session_state.selected_enquiry_id in enquiry_options.values():
            current_selection_index = list(enquiry_options.values()).index(st.session_state.selected_enquiry_id)
        elif enquiry_options: # Default to first if previous selection invalid or none
            st.session_state.selected_enquiry_id = list(enquiry_options.values())[0]

        selected_enquiry_label = st.selectbox(
            "Select an Enquiry:", 
            options=list(enquiry_options.keys()), # Ensure options is a list
            key="enquiry_selector",
            index = current_selection_index
        )
        
        if selected_enquiry_label: # Update based on actual selection
            st.session_state.selected_enquiry_id = enquiry_options[selected_enquiry_label]

        if st.session_state.selected_enquiry_id:
            enquiry_id = st.session_state.selected_enquiry_id
            enquiry_details, error_msg_details = get_enquiry_by_id(enquiry_id) # CHANGED
            
            if enquiry_details:
                st.subheader(f"Details for Enquiry: {enquiry_details['destination']} (ID: {enquiry_id[:8]}...)")
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"""
                        - **Destination:** {enquiry_details['destination']}
                        - **Days:** {enquiry_details['num_days']}
                        - **Travelers:** {enquiry_details['traveler_count']}
                        - **Trip Type:** {enquiry_details['trip_type']}
                        - **Status:** {enquiry_details.get('status', 'New')}
                    """)

                # --- Itinerary Section ---
                st.markdown("---")
                st.subheader("📋 AI Itinerary Generation")
                
                itinerary_data, error_msg_itinerary_get = get_itinerary_by_enquiry_id(enquiry_id) # CHANGED
                if error_msg_itinerary_get: st.warning(f"Could not load existing itinerary: {error_msg_itinerary_get}")

                st.session_state.current_itinerary = itinerary_data['itinerary_text'] if itinerary_data else None
                if itinerary_data:
                    st.info("Itinerary previously generated for this enquiry.")
                
                if st.button("Generate Itinerary with AI", key="gen_itinerary_btn"):
                    with st.spinner("Generating itinerary... This may take a moment."):
                        itinerary_text = generate_itinerary_llm(enquiry_details)
                        if "Error:" not in itinerary_text: # Assuming LLM util returns "Error:" prefix on failure
                            new_itinerary, error_msg_itinerary_add = add_itinerary(enquiry_id, itinerary_text) # CHANGED
                            if new_itinerary:
                                st.session_state.current_itinerary = itinerary_text
                                itinerary_data = new_itinerary # Update itinerary_data for quotation part
                                st.success("Itinerary generated and saved successfully!")
                            else:
                                st.error(f"Failed to save itinerary: {error_msg_itinerary_add if error_msg_itinerary_add else 'Unknown error'}") # CHANGED
                        else:
                            st.error(itinerary_text) 
                
                if st.session_state.current_itinerary:
                    with st.expander("View Generated Itinerary", expanded=True):
                        st.markdown(st.session_state.current_itinerary)

                # --- Quotation Section ---
                st.markdown("---")
                st.subheader("📄 AI Quotation Generation")

                quotation_data, error_msg_quote_get = get_quotation_by_enquiry_id(enquiry_id) # CHANGED
                if error_msg_quote_get: st.warning(f"Could not load existing quotation: {error_msg_quote_get}")

                st.session_state.current_quotation = quotation_data['quotation_text'] if quotation_data else None
                if quotation_data:
                    st.info("Quotation previously generated for this enquiry.")

                vendor_reply_data, error_msg_vendor_get = get_vendor_reply_by_enquiry_id(enquiry_id) # CHANGED
                if error_msg_vendor_get: st.warning(f"Could not load existing vendor reply: {error_msg_vendor_get}")
                st.session_state.current_vendor_reply = vendor_reply_data['reply_text'] if vendor_reply_data else None

                if st.button("Generate Quotation with AI", key="gen_quotation_btn", \
                             disabled=not (st.session_state.current_itinerary and st.session_state.current_vendor_reply)):
                    if not st.session_state.current_itinerary:
                        st.warning("Please generate an itinerary first.")
                    elif not st.session_state.current_vendor_reply:
                        st.warning("Please add a vendor reply for this enquiry first (Tab 3).")
                    else:
                        with st.spinner("Generating quotation... This may take a few moments."):
                            quotation_text = run_quotation_generation_graph(
                                enquiry_details,
                                st.session_state.current_itinerary,
                                st.session_state.current_vendor_reply
                            )
                            if "Error:" not in quotation_text: # Assuming LLM util returns "Error:" prefix on failure
                                new_quotation, error_msg_quote_add = add_quotation( # CHANGED
                                    enquiry_id, 
                                    quotation_text,
                                    itinerary_id=itinerary_data['id'] if itinerary_data else None, # Use potentially updated itinerary_data
                                    vendor_reply_id=vendor_reply_data['id'] if vendor_reply_data else None
                                )
                                if new_quotation:
                                    st.session_state.current_quotation = quotation_text
                                    st.success("Quotation generated and saved successfully!")
                                else:
                                    st.error(f"Failed to save quotation: {error_msg_quote_add if error_msg_quote_add else 'Unknown error'}") # CHANGED
                            else:
                                st.error(quotation_text)
                
                if st.session_state.current_quotation:
                    with st.expander("View Generated Quotation", expanded=True):
                        st.markdown(st.session_state.current_quotation)
            elif error_msg_details: # CHANGED
                 st.error(f"Could not load selected enquiry details: {error_msg_details}") # CHANGED
            else:
                 st.warning("Selected enquiry details could not be loaded or enquiry not found.")

        else:
            st.info("Select an enquiry to see details and generate documents.")


with tab3:
    st.header("3. Add Vendor Reply")
    
    enquiries_for_reply, error_msg_reply_get = get_enquiries() # CHANGED
    if error_msg_reply_get: # CHANGED
        st.error(f"Could not load enquiries for reply: {error_msg_reply_get}") # CHANGED
        enquiries_for_reply = []

    if not enquiries_for_reply:
        st.info("No enquiries available to add replies to.")
    else:
        reply_enquiry_options = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_for_reply}
        selected_reply_enquiry_label = st.selectbox(
            "Select Enquiry to Add Vendor Reply:",
            options=list(reply_enquiry_options.keys()), # Ensure options is a list
            key="reply_enquiry_selector"
        )

        if selected_reply_enquiry_label:
            reply_enquiry_id = reply_enquiry_options[selected_reply_enquiry_label]
            
            existing_vendor_reply, error_msg_existing_vendor = get_vendor_reply_by_enquiry_id(reply_enquiry_id) # CHANGED
            if error_msg_existing_vendor: st.warning(f"Could not check for existing vendor reply: {error_msg_existing_vendor}")

            if existing_vendor_reply:
                st.info("Vendor reply already exists for this enquiry:")
                st.text_area("Existing Vendor Reply", value=existing_vendor_reply['reply_text'], height=100, disabled=True, key="disp_vendor_reply")

            with st.form("vendor_reply_form"):
                vendor_reply_text = st.text_area("Vendor Reply (Plain Text - include pricing, inclusions, etc.)", height=200, key="new_vendor_reply_text")
                submitted_vendor_reply = st.form_submit_button("Submit Vendor Reply")

                if submitted_vendor_reply:
                    if not vendor_reply_text:
                        st.error("Vendor reply text cannot be empty.")
                    else:
                        with st.spinner("Adding vendor reply..."):
                            reply_data, error_msg_reply_add = add_vendor_reply(reply_enquiry_id, vendor_reply_text) # CHANGED
                            if reply_data:
                                st.success(f"Vendor reply added successfully for enquiry ID: {reply_enquiry_id[:8]}...")
                            else:
                                st.error(f"Failed to add vendor reply. {error_msg_reply_add if error_msg_reply_add else 'Unknown error'}") # CHANGED