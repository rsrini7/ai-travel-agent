import os
import json
import uuid # For unique filenames
from datetime import datetime # For timestamp in filenames
from dotenv import load_dotenv

if load_dotenv():
    print("APP.PY: .env file loaded successfully.")
else:
    print("APP.PY: .env file not found.")

import streamlit as st
from supabase_utils import (
    add_enquiry, get_enquiries, get_enquiry_by_id,
    add_itinerary, get_itinerary_by_enquiry_id,
    add_vendor_reply, get_vendor_reply_by_enquiry_id,
    add_quotation, update_quotation_storage_path, # Added update function
    add_client, get_client_by_enquiry_id,
    upload_file_to_storage, get_public_url, create_signed_url # Storage functions
)
from llm_utils import generate_places_suggestion_llm, run_quotation_generation_graph
from docx_utils import convert_pdf_bytes_to_docx_bytes

# --- CONFIGURATION ---
QUOTATIONS_BUCKET_NAME = "quotations" # Make sure this matches your bucket name in Supabase

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Automation MVP")

# Initialize session state variables
if 'selected_enquiry_id' not in st.session_state:
    st.session_state.selected_enquiry_id = None
if 'current_ai_suggestions' not in st.session_state:
    st.session_state.current_ai_suggestions = None
if 'current_ai_suggestions_id' not in st.session_state:
    st.session_state.current_ai_suggestions_id = None
if 'selected_enquiry_id_tab3' not in st.session_state:
    st.session_state.selected_enquiry_id_tab3 = None
if 'tab3_enquiry_details' not in st.session_state:
    st.session_state.tab3_enquiry_details = None
if 'tab3_client_name' not in st.session_state:
    st.session_state.tab3_client_name = "Valued Client"
if 'tab3_itinerary_info' not in st.session_state:
    st.session_state.tab3_itinerary_info = None
if 'tab3_vendor_reply_info' not in st.session_state:
    st.session_state.tab3_vendor_reply_info = None

# For managing the currently generated quotation in the DB
if 'tab3_current_quotation_db_id' not in st.session_state:
    st.session_state.tab3_current_quotation_db_id = None
if 'tab3_current_pdf_storage_path' not in st.session_state:
    st.session_state.tab3_current_pdf_storage_path = None
if 'tab3_current_docx_storage_path' not in st.session_state:
    st.session_state.tab3_current_docx_storage_path = None

if 'tab3_quotation_pdf_bytes' not in st.session_state: # For holding bytes for download button
    st.session_state.tab3_quotation_pdf_bytes = None
if 'tab3_quotation_docx_bytes' not in st.session_state: # For holding bytes for download button
    st.session_state.tab3_quotation_docx_bytes = None
if 'show_quotation_success_tab3' not in st.session_state:
    st.session_state.show_quotation_success_tab3 = False
if 'selected_ai_provider' not in st.session_state:
    st.session_state.selected_ai_provider = "OpenRouter"

if 'vendor_reply_saved_success_message' not in st.session_state:
    st.session_state.vendor_reply_saved_success_message = None # Or False

tab1, tab2, tab3 = st.tabs([
    "📝 New Enquiry",
    "🔍 Manage Enquiries & Itinerary",
    "✍️ Add Vendor Reply & Generate Quotation"
])

# --- AI Provider Selection (Global Sidebar) ---
st.sidebar.subheader("⚙️ AI Configuration")
# ... (sidebar code remains the same)
ai_provider_options = ["Gemini", "OpenRouter"]
current_provider_index = ai_provider_options.index(st.session_state.selected_ai_provider) if st.session_state.selected_ai_provider in ai_provider_options else 0
selected_provider = st.sidebar.selectbox(
    "Select AI Provider:",
    options=ai_provider_options,
    index=current_provider_index,
    key="ai_provider_selector_sidebar"
)
if selected_provider != st.session_state.selected_ai_provider:
    st.session_state.selected_ai_provider = selected_provider
    st.rerun()
st.sidebar.caption(f"Using: {st.session_state.selected_ai_provider}")
if st.session_state.selected_ai_provider == "OpenRouter":
    openrouter_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5")
    st.sidebar.caption(f"OpenRouter Model: {openrouter_model}")


with tab1: # New Enquiry
    st.header("1. Submit New Enquiry")
    # ... (Tab 1 code remains largely the same)
    with st.form("new_enquiry_form"):
        st.subheader("Travel Details")
        destination = st.text_input("Destination", placeholder="e.g., Paris, France")
        num_days = st.number_input("Number of Days", min_value=1, value=7)
        traveler_count = st.number_input("Number of Travelers", min_value=1, value=2)
        trip_type = st.selectbox("Trip Type", ["Leisure", "Business", "Adventure", "Honeymoon", "Family"])

        st.subheader("Client Information")
        client_name_input = st.text_input("Client Name", placeholder="John Doe")
        client_mobile_input = st.text_input("Mobile Number", placeholder="+91XXXXXXXXXX")
        client_city_input = st.text_input("City", placeholder="Mumbai")
        client_email_input = st.text_input("Email (optional)", placeholder="john@example.com")

        submitted_enquiry = st.form_submit_button("Submit Enquiry")
        if submitted_enquiry:
            if not destination:
                st.error("Destination is required.")
            elif not client_name_input or not client_mobile_input or not client_city_input:
                st.error("Client name, mobile and city are required.")
            else:
                with st.spinner("Submitting enquiry..."):
                    enquiry_data, error_msg = add_enquiry(destination, num_days, traveler_count, trip_type)
                    if enquiry_data:
                        client_data, client_error = add_client(
                            enquiry_id=enquiry_data['id'],
                            name=client_name_input,
                            mobile=client_mobile_input,
                            city=client_city_input,
                            email=client_email_input
                        )

                        if client_data:
                            st.success(f"Enquiry and client information submitted successfully! ID: {enquiry_data['id']}")
                            st.session_state.selected_enquiry_id = enquiry_data['id']
                            st.session_state.current_ai_suggestions = None
                            st.session_state.current_ai_suggestions_id = None
                            st.session_state.selected_enquiry_id_tab3 = enquiry_data['id'] # Auto-select in Tab 3
                            st.session_state.tab3_enquiry_details = None # Force reload in Tab 3
                            st.session_state.tab3_client_name = client_name_input
                            st.session_state.tab3_itinerary_info = None
                            st.session_state.tab3_vendor_reply_info = None
                            st.session_state.tab3_quotation_pdf_bytes = None
                            st.session_state.tab3_quotation_docx_bytes = None
                            st.session_state.tab3_current_quotation_db_id = None # Reset
                            st.session_state.tab3_current_pdf_storage_path = None
                            st.session_state.tab3_current_docx_storage_path = None
                            st.session_state.show_quotation_success_tab3 = False
                        else:
                            st.error(f"Enquiry submitted (ID: {enquiry_data['id']}) but failed to save client information. {client_error if client_error else 'Unknown error'}")
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}")


with tab2: # Manage Enquiries & Itinerary
    st.header("2. Manage Enquiries & Generate Itinerary")
    # ... (Tab 2 code remains the same as your previous full version)
    enquiries_list_tab2, error_msg_enq_list_tab2 = get_enquiries()
    if error_msg_enq_list_tab2:
        st.error(f"Could not load enquiries: {error_msg_enq_list_tab2}")
        enquiries_list_tab2 = []

    if not enquiries_list_tab2:
        st.info("No enquiries found. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id = None
    else:
        enquiry_options_tab2 = {f"{e['id'][:8]}... - {e['destination']} ({e['created_at'][:10]})": e['id'] for e in enquiries_list_tab2}

        if st.session_state.selected_enquiry_id not in enquiry_options_tab2.values():
            st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0] if enquiry_options_tab2 else None

        current_selection_index_tab2 = 0
        if st.session_state.selected_enquiry_id and enquiry_options_tab2:
            try:
                current_selection_index_tab2 = list(enquiry_options_tab2.values()).index(st.session_state.selected_enquiry_id)
            except ValueError:
                st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0]
                current_selection_index_tab2 = 0

        prev_selected_enquiry_id_tab2 = st.session_state.selected_enquiry_id
        selected_enquiry_label_tab2 = st.selectbox(
            "Select an Enquiry for Itinerary Generation:",
            options=list(enquiry_options_tab2.keys()),
            index=current_selection_index_tab2,
            key="enquiry_selector_tab2"
        )

        if selected_enquiry_label_tab2:
            st.session_state.selected_enquiry_id = enquiry_options_tab2[selected_enquiry_label_tab2]

        if st.session_state.selected_enquiry_id != prev_selected_enquiry_id_tab2:
            st.session_state.current_ai_suggestions = None
            st.session_state.current_ai_suggestions_id = None
            st.rerun()

        if st.session_state.selected_enquiry_id:
            enquiry_id_tab2 = st.session_state.selected_enquiry_id
            enquiry_details_tab2, error_msg_details_tab2 = get_enquiry_by_id(enquiry_id_tab2)

            if enquiry_details_tab2:
                if st.session_state.current_ai_suggestions is None or st.session_state.current_ai_suggestions_id is None: # or if enquiry_id changed
                    ai_suggestions_data_tab2, _ = get_itinerary_by_enquiry_id(enquiry_id_tab2)
                    if ai_suggestions_data_tab2:
                        st.session_state.current_ai_suggestions = ai_suggestions_data_tab2['itinerary_text']
                        st.session_state.current_ai_suggestions_id = ai_suggestions_data_tab2['id']
                    else:
                        st.session_state.current_ai_suggestions = None
                        st.session_state.current_ai_suggestions_id = None

                st.subheader(f"Details for Enquiry: {enquiry_details_tab2['destination']} (ID: {enquiry_id_tab2[:8]}...)")
                st.markdown(f"""
                    - **Destination:** {enquiry_details_tab2['destination']}
                    - **Days:** {enquiry_details_tab2['num_days']}
                    - **Travelers:** {enquiry_details_tab2['traveler_count']}
                    - **Trip Type:** {enquiry_details_tab2['trip_type']}
                    - **Status:** {enquiry_details_tab2.get('status', 'New')}
                """)

                st.markdown("---")
                st.subheader(f"💡 AI Places/Attraction Suggestions (using {st.session_state.selected_ai_provider})")

                if st.session_state.current_ai_suggestions:
                    with st.expander("View AI Generated Suggestions", expanded=True):
                        st.markdown(st.session_state.current_ai_suggestions)
                else:
                    st.caption("No AI suggestions generated yet for this enquiry.")

                if st.button(f"Generate Places Suggestions with {st.session_state.selected_ai_provider}", key="gen_ai_suggestions_btn_tab2"):
                    if 'show_ai_suggestion_success_tab2' not in st.session_state:
                        st.session_state.show_ai_suggestion_success_tab2 = False
                    with st.spinner(f"Generating AI suggestions with {st.session_state.selected_ai_provider}..."):
                        suggestions_text = generate_places_suggestion_llm(
                            enquiry_details_tab2,
                            provider=st.session_state.selected_ai_provider
                        )
                        if "Error:" not in suggestions_text and "Critical error" not in suggestions_text:
                            new_suggestion_record, error_msg_sugg_add = add_itinerary(enquiry_id_tab2, suggestions_text)
                            if new_suggestion_record:
                                st.session_state.current_ai_suggestions = suggestions_text
                                st.session_state.current_ai_suggestions_id = new_suggestion_record['id']
                                st.session_state.show_ai_suggestion_success_tab2 = True
                                st.rerun()
                            else:
                                st.error(f"Failed to save AI suggestions: {error_msg_sugg_add or 'Unknown error'}")
                        else:
                            st.error(suggestions_text)
                if st.session_state.get('show_ai_suggestion_success_tab2', False):
                    st.success("AI Place suggestions generated and saved successfully!")
                    st.session_state.show_ai_suggestion_success_tab2 = False
            elif error_msg_details_tab2:
                 st.error(f"Could not load selected enquiry details: {error_msg_details_tab2}")
            else:
                 st.warning("Selected enquiry details could not be loaded or enquiry not found.")
        else:
            st.info("Select an enquiry to see details and generate itinerary.")


with tab3: # Add Vendor Reply & Generate Quotation
    st.header("3. Add Vendor Reply & Generate Quotation")
    
    # Display the one-time success message if set
    if st.session_state.get('vendor_reply_saved_success_message'):
        st.success(st.session_state.vendor_reply_saved_success_message)
        st.session_state.vendor_reply_saved_success_message = None # Clear the message after displaying
    
    enquiries_list_tab3, error_msg_enq_list_tab3 = get_enquiries()
    if error_msg_enq_list_tab3:
        st.error(f"Could not load enquiries for this tab: {error_msg_enq_list_tab3}")
        enquiries_list_tab3 = []

    if not enquiries_list_tab3:
        st.info("No enquiries available. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id_tab3 = None
    else:
        enquiry_options_tab3 = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_list_tab3}

        if st.session_state.selected_enquiry_id_tab3 not in enquiry_options_tab3.values():
            st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0] if enquiry_options_tab3 else None

        current_selection_index_tab3 = 0
        if st.session_state.selected_enquiry_id_tab3 and enquiry_options_tab3:
            try:
                current_selection_index_tab3 = list(enquiry_options_tab3.values()).index(st.session_state.selected_enquiry_id_tab3)
            except ValueError:
                st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0]
                current_selection_index_tab3 = 0

        prev_selected_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3
        selected_enquiry_label_tab3 = st.selectbox(
            "Select Enquiry for Vendor Reply & Quotation:",
            options=list(enquiry_options_tab3.keys()),
            index=current_selection_index_tab3,
            key="enquiry_selector_tab3"
        )

        if selected_enquiry_label_tab3:
            st.session_state.selected_enquiry_id_tab3 = enquiry_options_tab3[selected_enquiry_label_tab3]

        if st.session_state.selected_enquiry_id_tab3 != prev_selected_enquiry_id_tab3:
            # Reset all tab3 specific states when enquiry changes
            st.session_state.tab3_enquiry_details = None
            st.session_state.tab3_client_name = "Valued Client"
            st.session_state.tab3_itinerary_info = None
            st.session_state.tab3_vendor_reply_info = None
            st.session_state.tab3_quotation_pdf_bytes = None
            st.session_state.tab3_quotation_docx_bytes = None
            st.session_state.tab3_current_quotation_db_id = None # Crucial reset
            st.session_state.tab3_current_pdf_storage_path = None
            st.session_state.tab3_current_docx_storage_path = None
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            # Load details if not already loaded for the current active_enquiry_id_tab3
            force_reload_tab3_data = False
            if st.session_state.tab3_enquiry_details is None or st.session_state.tab3_enquiry_details.get('id') != active_enquiry_id_tab3:
                force_reload_tab3_data = True

            # Additionally, you might introduce a flag that Tab2 sets to true after itinerary generation
            # e.g., if st.session_state.get('itinerary_updated_by_tab2'):
            # force_reload_tab3_data = True
            # st.session_state.itinerary_updated_by_tab2 = False # Reset the flag

            if force_reload_tab3_data:
                # st.write(f"[DEBUG Tab3] Forcing reload of all data for enquiry: {active_enquiry_id_tab3}") # Optional Debug
                # Load Enquiry Details
                details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
                st.session_state.tab3_enquiry_details = details

                # Load Client Name
                client_data_for_tab3, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_client_name = client_data_for_tab3["name"] if client_data_for_tab3 and client_data_for_tab3.get("name") else "Valued Client"
                
                # Load Vendor Reply (this logic seems okay as it's specific to tab3's workflow)
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_vendor_reply_info = {
                    'text': vendor_reply_data['reply_text'] if vendor_reply_data else None,
                    'id': vendor_reply_data['id'] if vendor_reply_data else None,
                    'enquiry_id_loaded_for': active_enquiry_id_tab3
                }
                # Reset quotation related states as well if enquiry changed
                st.session_state.tab3_quotation_pdf_bytes = None
                st.session_state.tab3_quotation_docx_bytes = None
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
                st.session_state.show_quotation_success_tab3 = False


            # ALWAYS Fetch Itinerary for Tab 3 when it's active for an enquiry,
            # as it might have been updated by Tab 2.
            # This overrides the previous conditional load for itinerary in Tab 3.
            # st.write(f"[DEBUG Tab3] Fetching itinerary for {active_enquiry_id_tab3} every time Tab3 logic runs for it.") # Optional Debug
            itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
            if itinerary_data_tab3:
                st.session_state.tab3_itinerary_info = {
                    'text': itinerary_data_tab3['itinerary_text'],
                    'id': itinerary_data_tab3['id'],
                    'enquiry_id_loaded_for': active_enquiry_id_tab3 # Still useful for internal checks if needed
                }
            else:
                st.session_state.tab3_itinerary_info = {
                    'text': "No itinerary found in database for this enquiry.", # More accurate message
                    'id': None,
                    'enquiry_id_loaded_for': active_enquiry_id_tab3
                }
                
            if st.session_state.tab3_enquiry_details:
                st.subheader(f"Working with Enquiry for {st.session_state.tab3_client_name}: {st.session_state.tab3_enquiry_details['destination']} (ID: {active_enquiry_id_tab3[:8]}...)")
                # ... (display enquiry details - same as before)
                cols_details_tab3 = st.columns(2)
                with cols_details_tab3[0]:
                    st.markdown(f"""
                        - **Destination:** {st.session_state.tab3_enquiry_details['destination']}
                        - **Days:** {st.session_state.tab3_enquiry_details['num_days']}
                        - **Travelers:** {st.session_state.tab3_enquiry_details['traveler_count']}
                    """)
                with cols_details_tab3[1]:
                     st.markdown(f"""
                        - **Trip Type:** {st.session_state.tab3_enquiry_details['trip_type']}
                        - **Status:** {st.session_state.tab3_enquiry_details.get('status', 'New')}
                    """)

                if st.session_state.tab3_itinerary_info and \
                    st.session_state.tab3_itinerary_info.get('text') and \
                    st.session_state.tab3_itinerary_info['text'] not in ["No itinerary generated yet.", "No itinerary found in database for this enquiry."]:
                        with st.expander("View AI Generated Itinerary/Suggestions", expanded=False):
                            st.markdown(st.session_state.tab3_itinerary_info['text'])
                else:
                    st.caption(st.session_state.tab3_itinerary_info.get('text', "No itinerary information available.")) # Display the text from the loaded info

                st.markdown("---")
                st.subheader("✍️ Add/View Vendor Reply")
                current_vendor_reply_text = st.session_state.tab3_vendor_reply_info.get('text', "") if st.session_state.tab3_vendor_reply_info else ""
                # ... (Vendor reply form - same as before, but ensure reset of quotation IDs on submit)
                if current_vendor_reply_text:
                    with st.expander("View Current Vendor Reply", expanded=False):
                        st.text_area("Existing Vendor Reply", value=current_vendor_reply_text, height=150, disabled=True, key=f"disp_vendor_reply_tab3_{active_enquiry_id_tab3}")
                else:
                    st.caption("No vendor reply submitted yet for this enquiry.")

                with st.form(key=f"vendor_reply_form_tab3_{active_enquiry_id_tab3}"):
                    vendor_reply_text_input = st.text_area(
                        "Vendor Reply Text (Pricing, Inclusions, etc.)",
                        height=200,
                        key=f"new_vendor_reply_text_tab3_{active_enquiry_id_tab3}",
                        value=st.session_state.tab3_vendor_reply_info.get('text', "") if st.session_state.tab3_vendor_reply_info else ""
                    )
                    submitted_vendor_reply = st.form_submit_button("Submit/Update Vendor Reply")

                    if submitted_vendor_reply:
                        if not vendor_reply_text_input:
                            st.error("Vendor reply text cannot be empty.")
                        else:
                            with st.spinner("Saving vendor reply..."):
                                reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
                                if reply_data:
                                    # Set the success message flag
                                    st.session_state.vendor_reply_saved_success_message = f"Vendor reply saved successfully for enquiry ID: {active_enquiry_id_tab3[:8]}..."
                                    
                                    # Update session state with new data *before* rerun
                                    st.session_state.tab3_vendor_reply_info = {
                                        'text': reply_data['reply_text'],
                                        'id': reply_data['id'],
                                        'enquiry_id_loaded_for': active_enquiry_id_tab3
                                    }
                                    # Reset states that depend on vendor reply
                                    st.session_state.tab3_quotation_pdf_bytes = None
                                    st.session_state.tab3_quotation_docx_bytes = None
                                    st.session_state.tab3_current_quotation_db_id = None
                                    st.session_state.tab3_current_pdf_storage_path = None
                                    st.session_state.tab3_current_docx_storage_path = None
                                    st.session_state.show_quotation_success_tab3 = False     
                                    st.rerun() # Rerun to reflect changes and show message at the top
                                else:
                                    st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")
                
                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")

                vendor_reply_available = st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info.get('text')
                # itinerary_available = st.session_state.tab3_itinerary_info and st.session_state.tab3_itinerary_info.get('text') and st.session_state.tab3_itinerary_info['text'] != "No itinerary generated yet."
                
                if not vendor_reply_available: st.warning("A vendor reply is required to generate quotations.")
                # if not itinerary_available: st.warning("An AI-generated itinerary is preferred.")

                generate_quotation_disabled = not (vendor_reply_available and st.session_state.tab3_enquiry_details)

                col1_gen, col2_gen = st.columns(2)
                # --- PDF GENERATION ---
                with col1_gen:
                    if st.button(f"Generate Quotation PDF with {st.session_state.selected_ai_provider}",
                                disabled=generate_quotation_disabled, key="generate_pdf_btn_tab3"):
                        st.session_state.tab3_quotation_pdf_bytes = None # Clear previous for download
                        st.session_state.show_quotation_success_tab3 = False # Reset success message
                        # st.session_state.tab3_current_quotation_db_id = None # Reset db id for new generation cycle

                        with st.spinner(f"Generating PDF data with {st.session_state.selected_ai_provider}..."):
                            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
                            current_enquiry_details_for_gen["itinerary_text_from_ui"] = st.session_state.tab3_itinerary_info.get('text', "Not available")

                            pdf_bytes_output, structured_data_dict = run_quotation_generation_graph(
                                current_enquiry_details_for_gen,
                                st.session_state.tab3_vendor_reply_info['text'],
                                st.session_state.selected_ai_provider
                            )
                        
                        if structured_data_dict and not structured_data_dict.get("error"):
                            is_error_pdf_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
                            if pdf_bytes_output and not is_error_pdf_content and len(pdf_bytes_output) > 1000:
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # For download button

                                # Upload PDF to Supabase Storage
                                with st.spinner("Uploading PDF to cloud storage..."):
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    file_name_in_storage = f"{active_enquiry_id_tab3}/quotation_{st.session_state.tab3_enquiry_details['destination'].replace(' ','_')}_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
                                    pdf_storage_path, upload_err = upload_file_to_storage(
                                        QUOTATIONS_BUCKET_NAME, file_name_in_storage, pdf_bytes_output, "application/pdf"
                                    )
                                
                                if upload_err:
                                    st.error(f"PDF generated, but failed to upload to storage: {upload_err}")
                                    # Still allow download of local bytes
                                else:
                                    st.info(f"PDF uploaded to storage: {pdf_storage_path}")
                                    st.session_state.tab3_current_pdf_storage_path = pdf_storage_path

                                # Save/Update quotation record in DB
                                with st.spinner("Saving quotation data to database..."):
                                    itinerary_id_to_save = st.session_state.tab3_itinerary_info.get('id')
                                    vendor_reply_id_to_save = st.session_state.tab3_vendor_reply_info.get('id')
                                    
                                    # Create a new quotation record for this generation attempt
                                    q_data, q_error = add_quotation(
                                        enquiry_id=active_enquiry_id_tab3,
                                        structured_data_json=structured_data_dict,
                                        itinerary_used_id=itinerary_id_to_save,
                                        vendor_reply_used_id=vendor_reply_id_to_save,
                                        pdf_storage_path=st.session_state.tab3_current_pdf_storage_path, # Use uploaded path
                                        docx_storage_path=st.session_state.tab3_current_docx_storage_path # Persist if already set
                                    )
                                    if q_error:
                                        st.error(f"Failed to save quotation data to DB: {q_error}")
                                    else:
                                        st.session_state.tab3_current_quotation_db_id = q_data['id'] # Store new DB ID
                                        st.success("Quotation PDF generated, uploaded, and data saved!")
                                        st.session_state.show_quotation_success_tab3 = True
                            else: # PDF bytes are bad or too small
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Show error PDF for download
                                st.error("Failed to generate a valid quotation PDF. An error PDF might be available.")
                        else: # Error in structured_data_dict
                            err_msg = structured_data_dict.get('error', "Unknown") if structured_data_dict else "Graph error"
                            raw_out = structured_data_dict.get('raw_output', '') if structured_data_dict else ''
                            st.error(f"Failed to structure data for PDF: {err_msg}")
                            if raw_out: st.expander("Raw LLM Output").text(raw_out)
                            if pdf_bytes_output: st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output


                # --- DOCX GENERATION ---
                with col2_gen:
                    if st.button(f"Generate Quotation DOCX with {st.session_state.selected_ai_provider}",
                                disabled=generate_quotation_disabled, key="generate_docx_btn_tab3"):
                        st.session_state.tab3_quotation_docx_bytes = None # Clear previous for download

                        with st.spinner(f"Generating DOCX data with {st.session_state.selected_ai_provider}..."):
                            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
                            current_enquiry_details_for_gen["itinerary_text_from_ui"] = st.session_state.tab3_itinerary_info.get('text', "Not available")

                            # This re-runs graph; could be optimized if structured_data_dict from PDF gen is stored and reused
                            pdf_bytes_for_docx, structured_data_dict_docx = run_quotation_generation_graph(
                                current_enquiry_details_for_gen,
                                st.session_state.tab3_vendor_reply_info['text'],
                                st.session_state.selected_ai_provider
                            )

                        if structured_data_dict_docx and not structured_data_dict_docx.get("error"):
                            is_error_pdf_content_for_docx = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
                            if pdf_bytes_for_docx and not is_error_pdf_content_for_docx and len(pdf_bytes_for_docx) > 1000:
                                with st.spinner("Converting PDF to DOCX..."):
                                    docx_bytes_output = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
                                
                                if docx_bytes_output:
                                    st.session_state.tab3_quotation_docx_bytes = docx_bytes_output # For download

                                    # Upload DOCX to Supabase Storage
                                    with st.spinner("Uploading DOCX to cloud storage..."):
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        file_name_in_storage_docx = f"{active_enquiry_id_tab3}/quotation_{st.session_state.tab3_enquiry_details['destination'].replace(' ','_')}_{timestamp}_{uuid.uuid4().hex[:8]}.docx"
                                        docx_storage_path, upload_err_docx = upload_file_to_storage(
                                            QUOTATIONS_BUCKET_NAME, file_name_in_storage_docx, docx_bytes_output, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                        )

                                    if upload_err_docx:
                                        st.error(f"DOCX generated, but failed to upload to storage: {upload_err_docx}")
                                    else:
                                        st.info(f"DOCX uploaded to storage: {docx_storage_path}")
                                        st.session_state.tab3_current_docx_storage_path = docx_storage_path
                                    
                                    # Update existing or add new quotation record
                                    with st.spinner("Saving/updating quotation data for DOCX..."):
                                        if st.session_state.tab3_current_quotation_db_id: # DB record from PDF gen exists
                                            _, update_err = update_quotation_storage_path(st.session_state.tab3_current_quotation_db_id, 'docx_storage_path', st.session_state.tab3_current_docx_storage_path)
                                            if update_err: st.error(f"Failed to update DOCX path in DB: {update_err}")
                                            else: st.success("Quotation DOCX generated, uploaded, and DB record updated!")
                                        else: # No prior PDF generation in this session, create new record
                                            itinerary_id_to_save = st.session_state.tab3_itinerary_info.get('id')
                                            vendor_reply_id_to_save = st.session_state.tab3_vendor_reply_info.get('id')
                                            q_data_docx, q_error_docx = add_quotation(
                                                enquiry_id=active_enquiry_id_tab3,
                                                structured_data_json=structured_data_dict_docx, # Use data from this DOCX flow
                                                itinerary_used_id=itinerary_id_to_save,
                                                vendor_reply_used_id=vendor_reply_id_to_save,
                                                pdf_storage_path=st.session_state.tab3_current_pdf_storage_path, # Persist if set
                                                docx_storage_path=st.session_state.tab3_current_docx_storage_path
                                            )
                                            if q_error_docx: st.error(f"Failed to save DOCX quotation data to DB: {q_error_docx}")
                                            else:
                                                st.session_state.tab3_current_quotation_db_id = q_data_docx['id']
                                                st.success("Quotation DOCX generated, uploaded, and new data record saved!")
                                else: # docx_bytes_output is None
                                    st.error("Failed to convert PDF to DOCX.")
                            else: # pdf_bytes_for_docx bad
                                st.error("Could not generate underlying PDF for DOCX conversion.")
                                if pdf_bytes_for_docx: st.download_button("Download Intermediate Error PDF", pdf_bytes_for_docx, "Error_PDF_for_DOCX.pdf", "application/pdf")
                        else: # Error in structured_data_dict_docx
                            err_msg_docx = structured_data_dict_docx.get('error', "Unknown") if structured_data_dict_docx else "Graph error"
                            raw_out_docx = structured_data_dict_docx.get('raw_output', '') if structured_data_dict_docx else ''
                            st.error(f"Failed to structure data for DOCX: {err_msg_docx}")
                            if raw_out_docx: st.expander("Raw LLM Output (DOCX attempt)").text(raw_out_docx)
                
                # --- DOWNLOAD BUTTONS ---
                # Placed outside the generation button columns, but still within tab3 active enquiry scope
                st.markdown("---")
                st.subheader("Download Generated Files")
                
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    if st.session_state.tab3_quotation_pdf_bytes:
                        st.download_button(
                            label="Download Generated PDF",
                            data=st.session_state.tab3_quotation_pdf_bytes,
                            file_name=f"Quotation_PDF_{st.session_state.tab3_enquiry_details.get('destination','Enquiry').replace(' ','_')}_{active_enquiry_id_tab3[:6]}.pdf",
                            mime="application/pdf", key="final_download_pdf_btn"
                        )
                    # Display link to stored PDF if available
                    if st.session_state.tab3_current_pdf_storage_path:
                        pdf_public_url = get_public_url(QUOTATIONS_BUCKET_NAME, st.session_state.tab3_current_pdf_storage_path)
                        if pdf_public_url:
                            st.markdown(f"[View Stored PDF]({pdf_public_url}) (if bucket is public)", unsafe_allow_html=True)
                        else: # Try signed URL if public URL fails or bucket is private
                            signed_url_pdf, err_signed_pdf = create_signed_url(QUOTATIONS_BUCKET_NAME, st.session_state.tab3_current_pdf_storage_path)
                            if signed_url_pdf:
                                st.markdown(f"[Download Stored PDF (Signed URL)]({signed_url_pdf})", unsafe_allow_html=True)
                            elif err_signed_pdf:
                                st.caption(f"Could not get URL for stored PDF: {err_signed_pdf}")


                with dl_col2:
                    if st.session_state.tab3_quotation_docx_bytes:
                        st.download_button(
                            label="Download Generated DOCX",
                            data=st.session_state.tab3_quotation_docx_bytes,
                            file_name=f"Quotation_DOCX_{st.session_state.tab3_enquiry_details.get('destination','Enquiry').replace(' ','_')}_{active_enquiry_id_tab3[:6]}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="final_download_docx_btn"
                        )
                    # Display link to stored DOCX if available
                    if st.session_state.tab3_current_docx_storage_path:
                        docx_public_url = get_public_url(QUOTATIONS_BUCKET_NAME, st.session_state.tab3_current_docx_storage_path)
                        if docx_public_url:
                            st.markdown(f"[View Stored DOCX]({docx_public_url}) (if bucket is public)", unsafe_allow_html=True)
                        else:
                            signed_url_docx, err_signed_docx = create_signed_url(QUOTATIONS_BUCKET_NAME, st.session_state.tab3_current_docx_storage_path)
                            if signed_url_docx:
                                st.markdown(f"[Download Stored DOCX (Signed URL)]({signed_url_docx})", unsafe_allow_html=True)
                            elif err_signed_docx:
                                st.caption(f"Could not get URL for stored DOCX: {err_signed_docx}")

            else: # if not st.session_state.tab3_enquiry_details
                 st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")
        else: # if not st.session_state.selected_enquiry_id_tab3
            st.info("Select an enquiry to manage its vendor reply and quotation.")