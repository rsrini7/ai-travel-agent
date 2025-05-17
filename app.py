# app.py
import os
from dotenv import load_dotenv

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
from llm_utils import generate_places_suggestion_llm, run_quotation_generation_graph 

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Automation MVP")

# Initialize session state variables
if 'selected_enquiry_id' not in st.session_state: # For Tab 2
    st.session_state.selected_enquiry_id = None
if 'current_ai_suggestions' not in st.session_state: # For Tab 2 (Itinerary text)
    st.session_state.current_ai_suggestions = None
if 'current_ai_suggestions_id' not in st.session_state: # For Tab 2 (Itinerary ID)
    st.session_state.current_ai_suggestions_id = None

# Session state for Tab 3
if 'selected_enquiry_id_tab3' not in st.session_state:
    st.session_state.selected_enquiry_id_tab3 = None
if 'tab3_enquiry_details' not in st.session_state:
    st.session_state.tab3_enquiry_details = None
if 'tab3_itinerary_info' not in st.session_state: # Stores {'text': ..., 'id': ...}
    st.session_state.tab3_itinerary_info = None
if 'tab3_vendor_reply_info' not in st.session_state: # Stores {'text': ..., 'id': ...}
    st.session_state.tab3_vendor_reply_info = None
if 'tab3_quotation_text' not in st.session_state:
    st.session_state.tab3_quotation_text = None
if 'show_quotation_success_tab3' not in st.session_state:
    st.session_state.show_quotation_success_tab3 = False


if 'selected_ai_provider' not in st.session_state:
    st.session_state.selected_ai_provider = "Gemini" # Default AI provider

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
                        # Set as selected in Tab 2 for immediate follow-up if desired
                        st.session_state.selected_enquiry_id = enquiry_data['id']
                        st.session_state.current_ai_suggestions = None 
                        st.session_state.current_ai_suggestions_id = None
                        # Also set for Tab 3 if user navigates there
                        st.session_state.selected_enquiry_id_tab3 = enquiry_data['id']
                        st.session_state.tab3_enquiry_details = None
                        st.session_state.tab3_itinerary_info = None
                        st.session_state.tab3_vendor_reply_info = None
                        st.session_state.tab3_quotation_text = None
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
        
        # Ensure current selection is valid, default if not
        if st.session_state.selected_enquiry_id not in enquiry_options_tab2.values():
            st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0] if enquiry_options_tab2 else None
        
        current_selection_index_tab2 = 0
        if st.session_state.selected_enquiry_id and enquiry_options_tab2:
            try:
                current_selection_index_tab2 = list(enquiry_options_tab2.values()).index(st.session_state.selected_enquiry_id)
            except ValueError: # If ID somehow not in list, default to first
                st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0]
                current_selection_index_tab2 = 0

        prev_selected_enquiry_id_tab2 = st.session_state.selected_enquiry_id
        selected_enquiry_label_tab2 = st.selectbox(
            "Select an Enquiry for Itinerary Generation:", 
            options=list(enquiry_options_tab2.keys()),
            index=current_selection_index_tab2,
            key="enquiry_selector_tab2"
        )
        
        if selected_enquiry_label_tab2: # Update session state if selection changes
            st.session_state.selected_enquiry_id = enquiry_options_tab2[selected_enquiry_label_tab2]

        # If selection changed, reset related data to force reload
        if st.session_state.selected_enquiry_id != prev_selected_enquiry_id_tab2:
            st.session_state.current_ai_suggestions = None
            st.session_state.current_ai_suggestions_id = None
            st.rerun()

        if st.session_state.selected_enquiry_id:
            enquiry_id_tab2 = st.session_state.selected_enquiry_id
            enquiry_details_tab2, error_msg_details_tab2 = get_enquiry_by_id(enquiry_id_tab2)
            
            if enquiry_details_tab2:
                # Load itinerary if not in session or if it's None for the current selection
                if st.session_state.current_ai_suggestions is None or st.session_state.current_ai_suggestions_id is None:
                    ai_suggestions_data_tab2, _ = get_itinerary_by_enquiry_id(enquiry_id_tab2)
                    if ai_suggestions_data_tab2:
                        st.session_state.current_ai_suggestions = ai_suggestions_data_tab2['itinerary_text']
                        st.session_state.current_ai_suggestions_id = ai_suggestions_data_tab2['id']
                    else: # No itinerary yet, clear session state for it
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
                    st.session_state.show_ai_suggestion_success_tab2 = False # Reset flag
                
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
        
        # Ensure current selection for Tab 3 is valid
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

        # If selection changed in Tab 3, reset its specific data to force reload
        if st.session_state.selected_enquiry_id_tab3 != prev_selected_enquiry_id_tab3:
            st.session_state.tab3_enquiry_details = None
            st.session_state.tab3_itinerary_info = None
            st.session_state.tab3_vendor_reply_info = None
            st.session_state.tab3_quotation_text = None
            st.session_state.show_quotation_success_tab3 = False # Reset success flag
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            # Load data for the selected enquiry in Tab 3 if not already loaded
            if st.session_state.tab3_enquiry_details is None:
                st.session_state.tab3_enquiry_details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
            
            if st.session_state.tab3_itinerary_info is None:
                itinerary_data, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
                if itinerary_data:
                    st.session_state.tab3_itinerary_info = {'text': itinerary_data['itinerary_text'], 'id': itinerary_data['id']}
                else:
                    st.session_state.tab3_itinerary_info = {'text': "No itinerary generated yet.", 'id': None}

            if st.session_state.tab3_vendor_reply_info is None:
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                if vendor_reply_data:
                    st.session_state.tab3_vendor_reply_info = {'text': vendor_reply_data['reply_text'], 'id': vendor_reply_data['id']}
                else:
                    st.session_state.tab3_vendor_reply_info = {'text': None, 'id': None}
            
            if st.session_state.tab3_quotation_text is None:
                quotation_data, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_quotation_text = quotation_data['quotation_text'] if quotation_data else None

            # Display Enquiry Details
            if st.session_state.tab3_enquiry_details:
                st.subheader(f"Working with Enquiry: {st.session_state.tab3_enquiry_details['destination']} (ID: {active_enquiry_id_tab3[:8]}...)")
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
                
                # Display Itinerary (read-only)
                if st.session_state.tab3_itinerary_info and st.session_state.tab3_itinerary_info['text']:
                    with st.expander("View AI Generated Itinerary/Suggestions (from Tab 2)", expanded=False):
                        st.markdown(st.session_state.tab3_itinerary_info['text'])
                else:
                    st.caption("No AI itinerary/suggestions found for this enquiry (generate in Tab 2).")
                
                st.markdown("---")
                st.subheader("✍️ Add/View Vendor Reply")
                
                if st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info['text']:
                    with st.expander("View Current Vendor Reply", expanded=False):
                        st.text_area("Existing Vendor Reply", value=st.session_state.tab3_vendor_reply_info['text'], height=150, disabled=True, key=f"disp_vendor_reply_tab3_{active_enquiry_id_tab3}")
                    st.info("A vendor reply already exists. Submitting a new one will replace the one used for new quotations.")
                else:
                    st.caption("No vendor reply submitted yet for this enquiry.")

                with st.form(key=f"vendor_reply_form_tab3_{active_enquiry_id_tab3}"):
                    vendor_reply_text_input = st.text_area("Vendor Reply Text (Pricing, Inclusions, etc.)", height=200, key=f"new_vendor_reply_text_tab3_{active_enquiry_id_tab3}", value=st.session_state.tab3_vendor_reply_info['text'] if st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info['text'] else "")
                    submitted_vendor_reply = st.form_submit_button("Submit/Update Vendor Reply")

                    if submitted_vendor_reply:
                        if not vendor_reply_text_input:
                            st.error("Vendor reply text cannot be empty.")
                        else:
                            with st.spinner("Saving vendor reply..."):
                                reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
                                if reply_data:
                                    st.success(f"Vendor reply saved successfully for enquiry ID: {active_enquiry_id_tab3[:8]}...")
                                    st.session_state.tab3_vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
                                    st.session_state.tab3_quotation_text = None # Clear old quotation as vendor reply changed
                                    st.session_state.show_quotation_success_tab3 = False
                                    st.rerun()
                                else:
                                    st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")
                
                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")

                if not (st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info['text']):
                    st.warning("A vendor reply is required to generate a quotation. Please add one above.")
                
                if st.session_state.tab3_quotation_text:
                     st.info("Quotation previously generated for this enquiry based on the current/previous vendor reply.")

                generate_quotation_disabled = not (st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info['text']) or not st.session_state.tab3_enquiry_details
                
                if st.button(f"Generate Quotation with {st.session_state.selected_ai_provider}", key="gen_quotation_btn_tab3", disabled=generate_quotation_disabled):
                    if st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info['text'] and st.session_state.tab3_enquiry_details:
                        with st.spinner(f"Generating quotation with {st.session_state.selected_ai_provider}... This may take moments."):
                            quotation_text_output = run_quotation_generation_graph(
                                st.session_state.tab3_enquiry_details,
                                st.session_state.tab3_vendor_reply_info['text'],
                                provider=st.session_state.selected_ai_provider
                            )
                            if "Critical error" not in quotation_text_output and "Error:" not in quotation_text_output :
                                itinerary_id_to_link = st.session_state.tab3_itinerary_info['id'] if st.session_state.tab3_itinerary_info else None
                                vendor_reply_id_to_link = st.session_state.tab3_vendor_reply_info['id'] # Should exist if button enabled
                                
                                new_quotation, error_msg_quote_add = add_quotation(
                                    active_enquiry_id_tab3, quotation_text_output,
                                    itinerary_used_id=itinerary_id_to_link,
                                    vendor_reply_used_id=vendor_reply_id_to_link 
                                )
                                if new_quotation:
                                    st.session_state.tab3_quotation_text = quotation_text_output
                                    st.session_state.show_quotation_success_tab3 = True
                                    st.rerun()
                                else:
                                    st.error(f"Failed to save quotation: {error_msg_quote_add or 'Unknown error'}")
                            else:
                                st.error(f"Quotation generation failed: {quotation_text_output}")
                
                if st.session_state.get('show_quotation_success_tab3', False):
                    st.success("Quotation generated and saved successfully!")
                    # Flag is reset if selection changes or new vendor reply added.
                
                if st.session_state.tab3_quotation_text:
                    with st.expander("View Generated Quotation", expanded=True):
                        st.markdown(st.session_state.tab3_quotation_text)

            else: # if not st.session_state.tab3_enquiry_details
                 st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")
        else: # if not st.session_state.selected_enquiry_id_tab3
            st.info("Select an enquiry to manage its vendor reply and quotation.")