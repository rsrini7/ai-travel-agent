import os
import json # Added for handling JSON data
from dotenv import load_dotenv

if load_dotenv():
    print("APP.PY: .env file loaded successfully by app.py's initial load_dotenv().")
else:
    print("APP.PY: .env file not found by app.py's initial load_dotenv().")

import streamlit as st
# import pandas as pd # Pandas import remains, though direct usage in this file is minimal
from supabase_utils import (
    add_enquiry, get_enquiries, get_enquiry_by_id,
    add_itinerary, get_itinerary_by_enquiry_id,
    add_vendor_reply, get_vendor_reply_by_enquiry_id,
    add_quotation, # Ensure this is the updated version
    add_client, # For adding client info
    get_client_by_enquiry_id # For fetching client name for PDF
)
from llm_utils import generate_places_suggestion_llm, run_quotation_generation_graph
from docx_utils import convert_pdf_bytes_to_docx_bytes # For DOCX conversion

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
if 'tab3_client_name' not in st.session_state: # For storing client name in Tab 3
    st.session_state.tab3_client_name = "Valued Client"
if 'tab3_itinerary_info' not in st.session_state:
    st.session_state.tab3_itinerary_info = None
if 'tab3_vendor_reply_info' not in st.session_state:
    st.session_state.tab3_vendor_reply_info = None
if 'tab3_quotation_pdf_bytes' not in st.session_state:
    st.session_state.tab3_quotation_pdf_bytes = None
if 'tab3_quotation_docx_bytes' not in st.session_state: # Added for DOCX
    st.session_state.tab3_quotation_docx_bytes = None
if 'show_quotation_success_tab3' not in st.session_state:
    st.session_state.show_quotation_success_tab3 = False # General success flag for generation
if 'selected_ai_provider' not in st.session_state:
    st.session_state.selected_ai_provider = "OpenRouter" # Default or load from config

tab1, tab2, tab3 = st.tabs([
    "📝 New Enquiry",
    "🔍 Manage Enquiries & Itinerary",
    "✍️ Add Vendor Reply & Generate Quotation"
])

# --- AI Provider Selection (Global Sidebar) ---
st.sidebar.subheader("⚙️ AI Configuration")
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


with tab1:
    st.header("1. Submit New Enquiry")
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
                            # Reset relevant session states
                            st.session_state.selected_enquiry_id = enquiry_data['id']
                            st.session_state.current_ai_suggestions = None
                            st.session_state.current_ai_suggestions_id = None
                            st.session_state.selected_enquiry_id_tab3 = enquiry_data['id']
                            st.session_state.tab3_enquiry_details = None
                            st.session_state.tab3_client_name = client_name_input # Store client name for tab 3
                            st.session_state.tab3_itinerary_info = None
                            st.session_state.tab3_vendor_reply_info = None
                            st.session_state.tab3_quotation_pdf_bytes = None
                            st.session_state.tab3_quotation_docx_bytes = None # Reset DOCX
                            st.session_state.show_quotation_success_tab3 = False
                        else:
                            st.error(f"Enquiry submitted (ID: {enquiry_data['id']}) but failed to save client information. {client_error if client_error else 'Unknown error'}")
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}")

with tab2:
    st.header("2. Manage Enquiries & Generate Itinerary")
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
                if st.session_state.current_ai_suggestions is None or st.session_state.current_ai_suggestions_id is None:
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
                        if "Error:" not in suggestions_text and "Critical error" not in suggestions_text: # Basic error check
                            new_suggestion_record, error_msg_sugg_add = add_itinerary(enquiry_id_tab2, suggestions_text)
                            if new_suggestion_record:
                                st.session_state.current_ai_suggestions = suggestions_text
                                st.session_state.current_ai_suggestions_id = new_suggestion_record['id']
                                st.session_state.show_ai_suggestion_success_tab2 = True
                                st.rerun()
                            else:
                                st.error(f"Failed to save AI suggestions: {error_msg_sugg_add or 'Unknown error'}")
                        else:
                            st.error(suggestions_text) # Show LLM error if one occurred
                if st.session_state.get('show_ai_suggestion_success_tab2', False):
                    st.success("AI Place suggestions generated and saved successfully!")
                    st.session_state.show_ai_suggestion_success_tab2 = False

            elif error_msg_details_tab2:
                 st.error(f"Could not load selected enquiry details: {error_msg_details_tab2}")
            else:
                 st.warning("Selected enquiry details could not be loaded or enquiry not found.")
        else:
            st.info("Select an enquiry to see details and generate itinerary.")


with tab3:
    st.header("3. Add Vendor Reply & Generate Quotation")
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
            st.session_state.tab3_enquiry_details = None
            st.session_state.tab3_client_name = "Valued Client" # Reset client name
            st.session_state.tab3_itinerary_info = None
            st.session_state.tab3_vendor_reply_info = None
            st.session_state.tab3_quotation_pdf_bytes = None
            st.session_state.tab3_quotation_docx_bytes = None # Reset DOCX
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            # Load enquiry details if not already loaded
            if st.session_state.tab3_enquiry_details is None:
                details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
                st.session_state.tab3_enquiry_details = details
                # Fetch client details for this enquiry
                client_data_for_tab3, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
                if client_data_for_tab3 and client_data_for_tab3.get("name"):
                    st.session_state.tab3_client_name = client_data_for_tab3["name"]
                else:
                    st.session_state.tab3_client_name = "Valued Client" # Default if not found

            # Load itinerary if not already loaded or if it's stale
            if st.session_state.tab3_itinerary_info is None or \
               (st.session_state.tab3_itinerary_info.get('enquiry_id_loaded_for') != active_enquiry_id_tab3):
                itinerary_data, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
                if itinerary_data:
                    st.session_state.tab3_itinerary_info = {
                        'text': itinerary_data['itinerary_text'],
                        'id': itinerary_data['id'],
                        'enquiry_id_loaded_for': active_enquiry_id_tab3
                    }
                else: # Fallback or clear if no itinerary for current enquiry
                    st.session_state.tab3_itinerary_info = {'text': "No itinerary generated yet.", 'id': None, 'enquiry_id_loaded_for': active_enquiry_id_tab3}


            # Load vendor reply if not already loaded or stale
            if st.session_state.tab3_vendor_reply_info is None or \
               (st.session_state.tab3_vendor_reply_info.get('enquiry_id_loaded_for') != active_enquiry_id_tab3):
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                if vendor_reply_data:
                    st.session_state.tab3_vendor_reply_info = {
                        'text': vendor_reply_data['reply_text'],
                        'id': vendor_reply_data['id'],
                        'enquiry_id_loaded_for': active_enquiry_id_tab3
                    }
                else:
                    st.session_state.tab3_vendor_reply_info = {'text': None, 'id': None, 'enquiry_id_loaded_for': active_enquiry_id_tab3}

            if st.session_state.tab3_enquiry_details:
                st.subheader(f"Working with Enquiry for {st.session_state.tab3_client_name}: {st.session_state.tab3_enquiry_details['destination']} (ID: {active_enquiry_id_tab3[:8]}...)")
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

                if st.session_state.tab3_itinerary_info and st.session_state.tab3_itinerary_info.get('text') and st.session_state.tab3_itinerary_info['text'] != "No itinerary generated yet.":
                    with st.expander("View AI Generated Itinerary/Suggestions", expanded=False):
                        st.markdown(st.session_state.tab3_itinerary_info['text'])
                else:
                    st.caption("No AI itinerary/suggestions found for this enquiry (generate in Tab 2 or ensure one exists).")

                st.markdown("---")
                st.subheader("✍️ Add/View Vendor Reply")

                current_vendor_reply_text = st.session_state.tab3_vendor_reply_info.get('text', "") if st.session_state.tab3_vendor_reply_info else ""
                if current_vendor_reply_text:
                    with st.expander("View Current Vendor Reply", expanded=False):
                        st.text_area("Existing Vendor Reply", value=current_vendor_reply_text, height=150, disabled=True, key=f"disp_vendor_reply_tab3_{active_enquiry_id_tab3}")
                    st.info("A vendor reply already exists. Submitting a new one will be used for new quotations.")
                else:
                    st.caption("No vendor reply submitted yet for this enquiry.")

                with st.form(key=f"vendor_reply_form_tab3_{active_enquiry_id_tab3}"):
                    vendor_reply_text_input = st.text_area("Vendor Reply Text (Pricing, Inclusions, etc.)", height=200, key=f"new_vendor_reply_text_tab3_{active_enquiry_id_tab3}", value=current_vendor_reply_text)
                    submitted_vendor_reply = st.form_submit_button("Submit/Update Vendor Reply")

                    if submitted_vendor_reply:
                        if not vendor_reply_text_input:
                            st.error("Vendor reply text cannot be empty.")
                        else:
                            with st.spinner("Saving vendor reply..."):
                                reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
                                if reply_data:
                                    st.success(f"Vendor reply saved successfully for enquiry ID: {active_enquiry_id_tab3[:8]}...")
                                    st.session_state.tab3_vendor_reply_info = {
                                        'text': reply_data['reply_text'],
                                        'id': reply_data['id'],
                                        'enquiry_id_loaded_for': active_enquiry_id_tab3
                                        }
                                    st.session_state.tab3_quotation_pdf_bytes = None
                                    st.session_state.tab3_quotation_docx_bytes = None # Reset DOCX
                                    st.session_state.show_quotation_success_tab3 = False
                                    st.rerun()
                                else:
                                    st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")

                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")

                vendor_reply_available = st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info.get('text')
                itinerary_available = st.session_state.tab3_itinerary_info and st.session_state.tab3_itinerary_info.get('text') and st.session_state.tab3_itinerary_info['text'] != "No itinerary generated yet."

                if not vendor_reply_available:
                    st.warning("A vendor reply is required to generate quotations. Please add one above.")
                if not itinerary_available:
                    st.warning("An AI-generated itinerary/suggestion is preferred for quotation generation. Please generate one in Tab 2 if missing.")

                generate_quotation_disabled = not (vendor_reply_available and st.session_state.tab3_enquiry_details)

                col1_gen, col2_gen = st.columns(2)
                with col1_gen:
                    if st.button(f"Generate Quotation PDF with {st.session_state.selected_ai_provider}",
                                disabled=generate_quotation_disabled,
                                key="generate_pdf_btn_tab3"):
                        st.session_state.tab3_quotation_pdf_bytes = None
                        st.session_state.show_quotation_success_tab3 = False

                        with st.spinner(f"Generating quotation PDF with {st.session_state.selected_ai_provider}... This may take moments."):
                            current_enquiry_details_for_generation = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_generation["client_name_actual"] = st.session_state.tab3_client_name
                            # Pass itinerary text to the graph if needed by prompts, or let graph fetch it
                            current_enquiry_details_for_generation["itinerary_text_from_ui"] = st.session_state.tab3_itinerary_info.get('text', "Not available")

                            pdf_bytes_output, structured_data_dict = run_quotation_generation_graph(
                                current_enquiry_details_for_generation,
                                st.session_state.tab3_vendor_reply_info['text'],
                                st.session_state.selected_ai_provider
                            )

                        if structured_data_dict and not structured_data_dict.get("error"):
                            is_error_pdf_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
                            if pdf_bytes_output and not is_error_pdf_content and len(pdf_bytes_output) > 1000: # Heuristic
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                                st.session_state.show_quotation_success_tab3 = True
                                st.success("Quotation PDF generated successfully!")

                                # Save structured data to Supabase
                                itinerary_id_to_save = st.session_state.tab3_itinerary_info.get('id')
                                vendor_reply_id_to_save = st.session_state.tab3_vendor_reply_info.get('id')

                                q_data, q_error = add_quotation(
                                    enquiry_id=active_enquiry_id_tab3,
                                    structured_data_json=structured_data_dict,
                                    itinerary_used_id=itinerary_id_to_save,
                                    vendor_reply_used_id=vendor_reply_id_to_save,
                                    pdf_storage_path=None, # Placeholder
                                    docx_storage_path=None # Placeholder
                                )
                                if q_error:
                                    st.error(f"PDF generated, but failed to save quotation's structured data to DB: {q_error}")
                                else:
                                    st.info("Quotation's structured data saved to database.")
                            else:
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Show error PDF if generated
                                st.error("Failed to generate a valid quotation PDF. An error PDF might be available for download.")
                        else:
                            err_msg = structured_data_dict.get('error', "Unknown error") if structured_data_dict else "Graph did not return structured data."
                            raw_output = structured_data_dict.get('raw_output', '') if structured_data_dict else ''
                            st.error(f"Failed to generate quotation due to error in data structuring: {err_msg}")
                            if raw_output:
                                st.expander("View Raw LLM Output from Structuring Node").text(raw_output)
                            if pdf_bytes_output: # An error PDF might have been made by the graph
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                                st.warning("An error PDF based on faulty data might be available for download.")

                if st.session_state.tab3_quotation_pdf_bytes:
                    st.download_button(
                        label="Download Quotation PDF",
                        data=st.session_state.tab3_quotation_pdf_bytes,
                        file_name=f"Quotation_PDF_{st.session_state.tab3_enquiry_details.get('destination','Enquiry').replace(' ','_')}_{active_enquiry_id_tab3[:6]}.pdf",
                        mime="application/pdf",
                        key="download_pdf_btn"
                    )

                with col2_gen:
                    if st.button(f"Generate Quotation DOCX with {st.session_state.selected_ai_provider}",
                                disabled=generate_quotation_disabled,
                                key="generate_docx_btn_tab3"):
                        st.session_state.tab3_quotation_docx_bytes = None # Clear previous
                        # show_quotation_success_tab3 is primarily for PDF, DOCX just generates
                        
                        with st.spinner(f"Generating quotation DOCX with {st.session_state.selected_ai_provider}... This may take moments."):
                            current_enquiry_details_for_generation = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_generation["client_name_actual"] = st.session_state.tab3_client_name
                            current_enquiry_details_for_generation["itinerary_text_from_ui"] = st.session_state.tab3_itinerary_info.get('text', "Not available")

                            pdf_bytes_for_docx, structured_data_dict_for_docx = run_quotation_generation_graph(
                                current_enquiry_details_for_generation,
                                st.session_state.tab3_vendor_reply_info['text'],
                                st.session_state.selected_ai_provider
                            )
                        
                        # The structured data would have been saved (or attempted) by the PDF generation flow if it ran.
                        # Here we focus on generating the DOCX for download.
                        if structured_data_dict_for_docx and not structured_data_dict_for_docx.get("error"):
                            is_error_pdf_content_for_docx = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
                            if pdf_bytes_for_docx and not is_error_pdf_content_for_docx and len(pdf_bytes_for_docx) > 1000:
                                with st.spinner("Converting PDF to DOCX..."):
                                    docx_bytes_output = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
                                if docx_bytes_output:
                                    st.session_state.tab3_quotation_docx_bytes = docx_bytes_output
                                    st.success("Quotation DOCX generated successfully!")
                                else:
                                    st.error("Failed to convert PDF to DOCX.")
                            else:
                                st.error("Could not generate underlying PDF for DOCX conversion. An error PDF might have been generated by the LLM process.")
                                if pdf_bytes_for_docx: # Make error PDF available if created
                                    st.download_button(
                                        label="Download Intermediate Error PDF (for DOCX)",
                                        data=pdf_bytes_for_docx,
                                        file_name=f"Error_PDF_for_DOCX_{active_enquiry_id_tab3[:6]}.pdf",
                                        mime="application/pdf",
                                        key="download_error_pdf_for_docx_btn"
                                    )
                        else:
                            err_msg_docx = structured_data_dict_for_docx.get('error', "Unknown error") if structured_data_dict_for_docx else "Graph did not return structured data for DOCX."
                            raw_output_docx = structured_data_dict_for_docx.get('raw_output', '') if structured_data_dict_for_docx else ''
                            st.error(f"Failed to generate data for DOCX: {err_msg_docx}")
                            if raw_output_docx:
                                st.expander("View Raw LLM Output from Structuring Node (DOCX attempt)").text(raw_output_docx)


                if st.session_state.tab3_quotation_docx_bytes:
                    st.download_button(
                        label="Download Quotation DOCX",
                        data=st.session_state.tab3_quotation_docx_bytes,
                        file_name=f"Quotation_DOCX_{st.session_state.tab3_enquiry_details.get('destination','Enquiry').replace(' ','_')}_{active_enquiry_id_tab3[:6]}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", # Correct MIME for .docx
                        key="download_docx_btn"
                    )

            else:
                 st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")
        else:
            st.info("Select an enquiry to manage its vendor reply and quotation.")