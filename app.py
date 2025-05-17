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
    add_itinerary, get_itinerary_by_enquiry_id, # Still used for AI suggestions
    add_vendor_reply, get_vendor_reply_by_enquiry_id,
    add_quotation, get_quotation_by_enquiry_id
)
# MODIFIED: Import new function name
from llm_utils import generate_places_suggestion_llm, run_quotation_generation_graph 

st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Travel Automation MVP")

# Initialize session state variables
if 'selected_enquiry_id' not in st.session_state:
    st.session_state.selected_enquiry_id = None
# RENAMED: This now stores AI-generated place suggestions
if 'current_ai_suggestions' not in st.session_state:
    st.session_state.current_ai_suggestions = None
# This specifically stores the ID of the AI suggestion record in DB
if 'current_ai_suggestions_id' not in st.session_state:
    st.session_state.current_ai_suggestions_id = None
if 'current_vendor_reply' not in st.session_state:
    st.session_state.current_vendor_reply = None
if 'current_quotation' not in st.session_state:
    st.session_state.current_quotation = None

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
                        st.session_state.current_ai_suggestions = None # Reset for new enquiry
                        st.session_state.current_ai_suggestions_id = None
                        st.session_state.current_vendor_reply = None
                        st.session_state.current_quotation = None
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}")

with tab2:
    st.header("2. Manage Enquiries & Generate Documents")
    
    enquiries_list, error_msg_enq_list = get_enquiries()
    if error_msg_enq_list:
        st.error(f"Could not load enquiries: {error_msg_enq_list}")
        enquiries_list = []

    if not enquiries_list:
        st.info("No enquiries found. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id = None 
    else:
        enquiry_options = {f"{e['id'][:8]}... - {e['destination']} ({e['created_at'][:10]})": e['id'] for e in enquiries_list}
        
        # Manage selected_enquiry_id changes and persistence
        # If current selected_enquiry_id is no longer valid or was never set, try to pick one.
        if st.session_state.selected_enquiry_id not in enquiry_options.values():
            if enquiry_options: # If there are options, pick the first one
                 st.session_state.selected_enquiry_id = list(enquiry_options.values())[0]
            else: # No options left
                 st.session_state.selected_enquiry_id = None
        
        # Determine index for selectbox based on current session state ID
        current_selection_index = 0
        if st.session_state.selected_enquiry_id and enquiry_options:
            try:
                current_selection_index = list(enquiry_options.values()).index(st.session_state.selected_enquiry_id)
            except ValueError: # selected_enquiry_id not in current list, default to 0
                st.session_state.selected_enquiry_id = list(enquiry_options.values())[0] # Reselect first
                current_selection_index = 0


        # Store the previous ID to detect changes
        prev_selected_enquiry_id = st.session_state.selected_enquiry_id

        selected_enquiry_label = st.selectbox(
            "Select an Enquiry:", 
            options=list(enquiry_options.keys()),
            key="enquiry_selector", # Keep a stable key
            index=current_selection_index
        )
        
        if selected_enquiry_label:
            st.session_state.selected_enquiry_id = enquiry_options[selected_enquiry_label]

        # If enquiry selection changed, clear related session state items
        if st.session_state.selected_enquiry_id != prev_selected_enquiry_id:
            st.session_state.current_ai_suggestions = None
            st.session_state.current_ai_suggestions_id = None
            st.session_state.current_vendor_reply = None
            st.session_state.current_quotation = None
            # Force a re-run to reload data for the new enquiry
            st.rerun()


        if st.session_state.selected_enquiry_id:
            enquiry_id = st.session_state.selected_enquiry_id
            enquiry_details, error_msg_details = get_enquiry_by_id(enquiry_id)
            
            # Load existing data for the selected enquiry if not already in session state
            # or if it's None (meaning it was reset or never loaded)
            if enquiry_details and st.session_state.current_ai_suggestions is None:
                ai_suggestions_data, _ = get_itinerary_by_enquiry_id(enquiry_id) # Fetch AI suggestions
                if ai_suggestions_data:
                    st.session_state.current_ai_suggestions = ai_suggestions_data['itinerary_text']
                    st.session_state.current_ai_suggestions_id = ai_suggestions_data['id']
                else:
                    st.session_state.current_ai_suggestions = None # Explicitly None if not found
                    st.session_state.current_ai_suggestions_id = None


            if enquiry_details and st.session_state.current_vendor_reply is None:
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(enquiry_id)
                if vendor_reply_data:
                    st.session_state.current_vendor_reply = vendor_reply_data['reply_text']
                else:
                     st.session_state.current_vendor_reply = None # Explicitly None

            if enquiry_details and st.session_state.current_quotation is None:
                quotation_data, _ = get_quotation_by_enquiry_id(enquiry_id)
                if quotation_data:
                    st.session_state.current_quotation = quotation_data['quotation_text']
                else:
                    st.session_state.current_quotation = None # Explicitly None

            if enquiry_details:
                st.subheader(f"Details for Enquiry: {enquiry_details['destination']} (ID: {enquiry_id[:8]}...)")
                cols_details = st.columns(2)
                with cols_details[0]:
                    st.markdown(f"""
                        - **Destination:** {enquiry_details['destination']}
                        - **Days:** {enquiry_details['num_days']}
                        - **Travelers:** {enquiry_details['traveler_count']}
                        - **Trip Type:** {enquiry_details['trip_type']}
                        - **Status:** {enquiry_details.get('status', 'New')}
                    """)

                # --- AI Places Suggestion Section ---
                st.markdown("---")
                st.subheader("💡 AI Places/Attraction Suggestions")
                
                # Display existing AI suggestions if any
                if st.session_state.current_ai_suggestions:
                    with st.expander("View AI Generated Suggestions", expanded=False):
                        st.markdown(st.session_state.current_ai_suggestions)
                else:
                    st.caption("No AI suggestions generated yet for this enquiry.")

                if st.button("Generate Places Suggestions with AI", key="gen_ai_suggestions_btn"):
                    with st.spinner("Generating AI suggestions..."):
                        # MODIFIED: Call new function
                        suggestions_text = generate_places_suggestion_llm(enquiry_details)
                        if "Error:" not in suggestions_text:
                            # The 'itineraries' table now stores these suggestions
                            new_suggestion_record, error_msg_sugg_add = add_itinerary(enquiry_id, suggestions_text)
                            if new_suggestion_record:
                                st.session_state.current_ai_suggestions = suggestions_text
                                st.session_state.current_ai_suggestions_id = new_suggestion_record['id'] # Store ID
                                st.success("AI Place suggestions generated and saved successfully!")
                                st.rerun() # Rerun to update expander display
                            else:
                                st.error(f"Failed to save AI suggestions: {error_msg_sugg_add if error_msg_sugg_add else 'Unknown error'}")
                        else:
                            st.error(suggestions_text)
                
                # --- Quotation Section ---
                st.markdown("---")
                st.subheader("📄 AI Quotation Generation (from Vendor Reply)")

                # Display existing vendor reply if available (for user context before generating quote)
                if st.session_state.current_vendor_reply:
                    with st.expander("View Current Vendor Reply (used for quotation)", expanded=False):
                        st.markdown(st.session_state.current_vendor_reply)
                else:
                    st.warning("No vendor reply found for this enquiry. Please add one in 'Add Vendor Reply' tab to generate a quotation.")

                if st.session_state.current_quotation:
                    st.info("Quotation previously generated for this enquiry.")
                
                # MODIFIED: Quotation generation button logic
                generate_quotation_disabled = not st.session_state.current_vendor_reply
                if st.button("Generate Quotation with AI", key="gen_quotation_btn", disabled=generate_quotation_disabled):
                    if not st.session_state.current_vendor_reply:
                        st.warning("A vendor reply is required to generate a quotation. Please add one in Tab 3.")
                    else:
                        with st.spinner("Generating quotation using vendor reply... This may take a few moments."):
                            # MODIFIED: Call to run_quotation_generation_graph no longer needs AI itinerary text
                            quotation_text = run_quotation_generation_graph(
                                enquiry_details,
                                st.session_state.current_vendor_reply # Pass only vendor reply
                            )
                            if "Critical error" not in quotation_text and "Error:" not in quotation_text : # Adjusted error check
                                # itinerary_used_id can still be the ID of the AI *suggestions* if you want to link them
                                current_ai_sugg_id = st.session_state.current_ai_suggestions_id

                                # Get vendor reply ID
                                vendor_reply_data_for_id, _ = get_vendor_reply_by_enquiry_id(enquiry_id)
                                vendor_reply_id_to_link = vendor_reply_data_for_id['id'] if vendor_reply_data_for_id else None

                                new_quotation, error_msg_quote_add = add_quotation(
                                    enquiry_id, 
                                    quotation_text,
                                    itinerary_used_id=current_ai_sugg_id, # Link AI suggestions ID (optional)
                                    vendor_reply_used_id=vendor_reply_id_to_link 
                                )
                                if new_quotation:
                                    st.session_state.current_quotation = quotation_text
                                    st.success("Quotation generated and saved successfully!")
                                    st.rerun() # Rerun to show new quotation
                                else:
                                    st.error(f"Failed to save quotation: {error_msg_quote_add if error_msg_quote_add else 'Unknown error'}")
                            else:
                                st.error(f"Quotation generation failed: {quotation_text}")
                
                if st.session_state.current_quotation:
                    with st.expander("View Generated Quotation", expanded=True):
                        st.markdown(st.session_state.current_quotation)

            elif error_msg_details:
                 st.error(f"Could not load selected enquiry details: {error_msg_details}")
            else:
                 st.warning("Selected enquiry details could not be loaded or enquiry not found.")
        else:
            st.info("Select an enquiry to see details and generate documents.")

with tab3:
    st.header("3. Add Vendor Reply")
    
    enquiries_for_reply, error_msg_reply_get_list = get_enquiries()
    if error_msg_reply_get_list:
        st.error(f"Could not load enquiries for reply: {error_msg_reply_get_list}")
        enquiries_for_reply = []

    if not enquiries_for_reply:
        st.info("No enquiries available to add replies to.")
    else:
        reply_enquiry_options = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_for_reply}
        
        # Try to maintain selection if possible, or default
        selected_reply_enq_id_for_form = st.session_state.get('selected_reply_enquiry_id_for_form', None)
        if selected_reply_enq_id_for_form not in reply_enquiry_options.values() and reply_enquiry_options:
            selected_reply_enq_id_for_form = list(reply_enquiry_options.values())[0]
        
        idx_reply_select = 0
        if selected_reply_enq_id_for_form and reply_enquiry_options:
            try:
                idx_reply_select = list(reply_enquiry_options.values()).index(selected_reply_enq_id_for_form)
            except ValueError:
                idx_reply_select = 0


        selected_reply_enquiry_label = st.selectbox(
            "Select Enquiry to Add Vendor Reply:",
            options=list(reply_enquiry_options.keys()),
            key="reply_enquiry_selector",
            index=idx_reply_select
        )

        if selected_reply_enquiry_label:
            reply_enquiry_id = reply_enquiry_options[selected_reply_enquiry_label]
            st.session_state.selected_reply_enquiry_id_for_form = reply_enquiry_id # Persist selection for this tab

            existing_vendor_reply_data, error_msg_existing_vendor = get_vendor_reply_by_enquiry_id(reply_enquiry_id)
            if error_msg_existing_vendor: st.warning(f"Could not check for existing vendor reply: {error_msg_existing_vendor}")

            if existing_vendor_reply_data:
                st.info("Vendor reply already exists for this enquiry. Submitting a new one will add another record (latest will be used for quotes).")
                with st.expander("View Existing Vendor Reply", expanded=False):
                    st.text_area("Existing Vendor Reply", value=existing_vendor_reply_data['reply_text'], height=100, disabled=True, key=f"disp_vendor_reply_{reply_enquiry_id}")

            with st.form(key=f"vendor_reply_form_{reply_enquiry_id}"): # Unique key for form
                vendor_reply_text = st.text_area("Vendor Reply (Plain Text - include full itinerary, pricing, inclusions, etc.)", height=200, key=f"new_vendor_reply_text_{reply_enquiry_id}")
                submitted_vendor_reply = st.form_submit_button("Submit Vendor Reply")

                if submitted_vendor_reply:
                    if not vendor_reply_text:
                        st.error("Vendor reply text cannot be empty.")
                    else:
                        with st.spinner("Adding vendor reply..."):
                            reply_data, error_msg_reply_add = add_vendor_reply(reply_enquiry_id, vendor_reply_text)
                            if reply_data:
                                st.success(f"Vendor reply added successfully for enquiry ID: {reply_enquiry_id[:8]}...")
                                # If this reply was for the currently selected enquiry in Tab 2, update its vendor reply in session
                                if reply_enquiry_id == st.session_state.selected_enquiry_id:
                                    st.session_state.current_vendor_reply = vendor_reply_text
                                    st.session_state.current_quotation = None # Clear old quotation as vendor reply changed
                                st.rerun()
                            else:
                                st.error(f"Failed to add vendor reply. {error_msg_reply_add if error_msg_reply_add else 'Unknown error'}")