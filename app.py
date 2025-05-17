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
if 'selected_enquiry_id' not in st.session_state:
    st.session_state.selected_enquiry_id = None
if 'current_ai_suggestions' not in st.session_state:
    st.session_state.current_ai_suggestions = None
if 'current_ai_suggestions_id' not in st.session_state:
    st.session_state.current_ai_suggestions_id = None
if 'current_vendor_reply' not in st.session_state:
    st.session_state.current_vendor_reply = None
if 'current_quotation' not in st.session_state:
    st.session_state.current_quotation = None
if 'selected_ai_provider' not in st.session_state:
    st.session_state.selected_ai_provider = "Gemini" # Default AI provider

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
                        st.session_state.current_ai_suggestions = None 
                        st.session_state.current_ai_suggestions_id = None
                        st.session_state.current_vendor_reply = None
                        st.session_state.current_quotation = None
                        # Optionally switch to tab2 or trigger rerun if needed for immediate selection
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}")

with tab2:
    st.header("2. Manage Enquiries & Generate Documents")
    
    # --- AI Provider Selection ---
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter"]
    # Ensure current selection is valid, default if not
    if st.session_state.selected_ai_provider not in ai_provider_options:
        st.session_state.selected_ai_provider = "Gemini"
    
    current_provider_index = ai_provider_options.index(st.session_state.selected_ai_provider)

    selected_provider = st.sidebar.selectbox(
        "Select AI Provider:",
        options=ai_provider_options,
        index=current_provider_index,
        key="ai_provider_selector" 
    )
    # Update session state if selection changes
    if selected_provider != st.session_state.selected_ai_provider:
        st.session_state.selected_ai_provider = selected_provider
        st.rerun() # Rerun to reflect provider change immediately if necessary for other UI elements

    st.sidebar.caption(f"Using: {st.session_state.selected_ai_provider}")
    if st.session_state.selected_ai_provider == "OpenRouter":
        openrouter_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5")
        st.sidebar.caption(f"OpenRouter Model: {openrouter_model}")


    enquiries_list, error_msg_enq_list = get_enquiries()
    if error_msg_enq_list:
        st.error(f"Could not load enquiries: {error_msg_enq_list}")
        enquiries_list = []

    if not enquiries_list:
        st.info("No enquiries found. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id = None 
    else:
        enquiry_options = {f"{e['id'][:8]}... - {e['destination']} ({e['created_at'][:10]})": e['id'] for e in enquiries_list}
        
        if st.session_state.selected_enquiry_id not in enquiry_options.values():
            st.session_state.selected_enquiry_id = list(enquiry_options.values())[0] if enquiry_options else None
        
        current_selection_index = 0
        if st.session_state.selected_enquiry_id and enquiry_options:
            try:
                current_selection_index = list(enquiry_options.values()).index(st.session_state.selected_enquiry_id)
            except ValueError:
                st.session_state.selected_enquiry_id = list(enquiry_options.values())[0]
                current_selection_index = 0

        prev_selected_enquiry_id = st.session_state.selected_enquiry_id
        selected_enquiry_label = st.selectbox(
            "Select an Enquiry:", 
            options=list(enquiry_options.keys()),
            index=current_selection_index,
            key="enquiry_selector_tab2"
        )
        
        if selected_enquiry_label:
            st.session_state.selected_enquiry_id = enquiry_options[selected_enquiry_label]

        if st.session_state.selected_enquiry_id != prev_selected_enquiry_id:
            st.session_state.current_ai_suggestions = None
            st.session_state.current_ai_suggestions_id = None
            st.session_state.current_vendor_reply = None
            st.session_state.current_quotation = None
            st.rerun()

        if st.session_state.selected_enquiry_id:
            enquiry_id = st.session_state.selected_enquiry_id
            enquiry_details, error_msg_details = get_enquiry_by_id(enquiry_id)
            
            if enquiry_details:
                # Load related data if not in session or if it's None
                if st.session_state.current_ai_suggestions is None:
                    ai_suggestions_data, _ = get_itinerary_by_enquiry_id(enquiry_id)
                    if ai_suggestions_data:
                        st.session_state.current_ai_suggestions = ai_suggestions_data['itinerary_text']
                        st.session_state.current_ai_suggestions_id = ai_suggestions_data['id']
                    else:
                        st.session_state.current_ai_suggestions = None
                        st.session_state.current_ai_suggestions_id = None

                if st.session_state.current_vendor_reply is None:
                    vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(enquiry_id)
                    st.session_state.current_vendor_reply = vendor_reply_data['reply_text'] if vendor_reply_data else None

                if st.session_state.current_quotation is None:
                    quotation_data, _ = get_quotation_by_enquiry_id(enquiry_id)
                    st.session_state.current_quotation = quotation_data['quotation_text'] if quotation_data else None

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

                st.markdown("---")
                st.subheader(f"💡 AI Places/Attraction Suggestions (using {st.session_state.selected_ai_provider})")
                
                if st.session_state.current_ai_suggestions:
                    with st.expander("View AI Generated Suggestions", expanded=False):
                        st.markdown(st.session_state.current_ai_suggestions)
                else:
                    st.caption("No AI suggestions generated yet for this enquiry.")

                if st.button(f"Generate Places Suggestions with {st.session_state.selected_ai_provider}", key="gen_ai_suggestions_btn"):
                    if 'show_ai_suggestion_success' not in st.session_state:
                        st.session_state.show_ai_suggestion_success = False
                    with st.spinner(f"Generating AI suggestions with {st.session_state.selected_ai_provider}..."):
                        suggestions_text = generate_places_suggestion_llm(
                            enquiry_details, 
                            provider=st.session_state.selected_ai_provider
                        )
                        if "Error:" not in suggestions_text and "Critical error" not in suggestions_text:
                            new_suggestion_record, error_msg_sugg_add = add_itinerary(enquiry_id, suggestions_text)
                            if new_suggestion_record:
                                st.session_state.current_ai_suggestions = suggestions_text
                                st.session_state.current_ai_suggestions_id = new_suggestion_record['id']
                                st.session_state.show_ai_suggestion_success = True
                                st.rerun()
                            else:
                                st.error(f"Failed to save AI suggestions: {error_msg_sugg_add or 'Unknown error'}")
                        else:
                            st.error(suggestions_text)
                if st.session_state.get('show_ai_suggestion_success', False):
                    st.success("AI Place suggestions generated and saved successfully!")
                    st.session_state.show_ai_suggestion_success = False
                
                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")

                if st.session_state.current_vendor_reply:
                    with st.expander("View Current Vendor Reply (used for quotation)", expanded=False):
                        st.markdown(st.session_state.current_vendor_reply)
                else:
                    st.warning("No vendor reply found. Add one in 'Add Vendor Reply' tab to generate a quotation.")

                if st.session_state.current_quotation:
                    st.info("Quotation previously generated for this enquiry.")
                
                generate_quotation_disabled = not st.session_state.current_vendor_reply
                if st.button(f"Generate Quotation with {st.session_state.selected_ai_provider}", key="gen_quotation_btn", disabled=generate_quotation_disabled):
                    if st.session_state.current_vendor_reply: # Redundant check due to disabled state, but good for safety
                        with st.spinner(f"Generating quotation with {st.session_state.selected_ai_provider}... This may take moments."):
                            quotation_text = run_quotation_generation_graph(
                                enquiry_details,
                                st.session_state.current_vendor_reply,
                                provider=st.session_state.selected_ai_provider
                            )
                            if "Critical error" not in quotation_text and "Error:" not in quotation_text :
                                current_ai_sugg_id = st.session_state.current_ai_suggestions_id
                                vendor_reply_data_for_id, _ = get_vendor_reply_by_enquiry_id(enquiry_id)
                                vendor_reply_id_to_link = vendor_reply_data_for_id['id'] if vendor_reply_data_for_id else None

                                new_quotation, error_msg_quote_add = add_quotation(
                                    enquiry_id, quotation_text,
                                    itinerary_used_id=current_ai_sugg_id,
                                    vendor_reply_used_id=vendor_reply_id_to_link 
                                )
                                if new_quotation:
                                    st.session_state.current_quotation = quotation_text
                                    st.success("Quotation generated and saved successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to save quotation: {error_msg_quote_add or 'Unknown error'}")
                            else:
                                st.error(f"Quotation generation failed: {quotation_text}")
                
                if st.session_state.current_quotation:
                    with st.expander("View Generated Quotation", expanded=True):
                        st.markdown(st.session_state.current_quotation)

            elif error_msg_details:
                 st.error(f"Could not load selected enquiry details: {error_msg_details}")
            else: # enquiry_details is None, but no specific DB error
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
        
        selected_reply_enq_id_for_form = st.session_state.get('selected_reply_enquiry_id_for_form', None)
        if selected_reply_enq_id_for_form not in reply_enquiry_options.values() and reply_enquiry_options:
            selected_reply_enq_id_for_form = list(reply_enquiry_options.values())[0]
        
        idx_reply_select = 0
        if selected_reply_enq_id_for_form and reply_enquiry_options:
            try:
                idx_reply_select = list(reply_enquiry_options.values()).index(selected_reply_enq_id_for_form)
            except ValueError:
                idx_reply_select = 0
                if reply_enquiry_options: # If list has items, default to first one
                    selected_reply_enq_id_for_form = list(reply_enquiry_options.values())[0]


        selected_reply_enquiry_label = st.selectbox(
            "Select Enquiry to Add Vendor Reply:",
            options=list(reply_enquiry_options.keys()),
            index=idx_reply_select,
            key="reply_enquiry_selector"
        )

        if selected_reply_enquiry_label:
            reply_enquiry_id = reply_enquiry_options[selected_reply_enquiry_label]
            st.session_state.selected_reply_enquiry_id_for_form = reply_enquiry_id 

            existing_vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(reply_enquiry_id)
            
            if existing_vendor_reply_data:
                st.info("Vendor reply already exists for this enquiry. Submitting a new one will add another record (latest will be used for quotes).")
                with st.expander("View Existing Vendor Reply", expanded=False):
                    st.text_area("Existing Vendor Reply", value=existing_vendor_reply_data['reply_text'], height=100, disabled=True, key=f"disp_vendor_reply_{reply_enquiry_id}")

            with st.form(key=f"vendor_reply_form_{reply_enquiry_id}"):
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
                                if reply_enquiry_id == st.session_state.selected_enquiry_id:
                                    st.session_state.current_vendor_reply = vendor_reply_text
                                    st.session_state.current_quotation = None 
                                st.rerun()
                            else:
                                st.error(f"Failed to add vendor reply. {error_msg_reply_add or 'Unknown error'}")