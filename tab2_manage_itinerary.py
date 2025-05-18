import streamlit as st
from supabase_utils import (
    get_enquiries, get_enquiry_by_id,
    add_itinerary, get_itinerary_by_enquiry_id
)
from itinerary_generator import generate_places_suggestion_llm

def render_tab2():
    st.header("2. Manage Enquiries & Generate Itinerary")

    # Display one-time messages if set (e.g., from vendor reply save or itinerary save from Tab 2 itself)
    # This can also be from Tab1 if an enquiry was just created and auto-selected
    if st.session_state.get('vendor_reply_saved_success_message'):
        st.success(st.session_state.vendor_reply_saved_success_message)
        st.session_state.vendor_reply_saved_success_message = None # Clear after displaying

    enquiries_list_tab2, error_msg_enq_list_tab2 = get_enquiries()
    if error_msg_enq_list_tab2:
        st.error(f"Could not load enquiries: {error_msg_enq_list_tab2}")
        enquiries_list_tab2 = []

    if not enquiries_list_tab2:
        st.info("No enquiries found. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id = None # Clear selection if no enquiries
    else:
        enquiry_options_tab2 = {f"{e['id'][:8]}... - {e['destination']} ({e['created_at'][:10]})": e['id'] for e in enquiries_list_tab2}

        # Ensure selected_enquiry_id is valid or default to the first one
        if st.session_state.selected_enquiry_id not in enquiry_options_tab2.values():
            st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0] if enquiry_options_tab2 else None
            # If selection changed due to invalidity, reset itinerary states
            if st.session_state.selected_enquiry_id:
                st.session_state.current_ai_suggestions = None
                st.session_state.current_ai_suggestions_id = None
                st.session_state.itinerary_loaded_for_tab2 = None

        current_selection_index_tab2 = 0
        if st.session_state.selected_enquiry_id and enquiry_options_tab2:
            try:
                current_selection_index_tab2 = list(enquiry_options_tab2.values()).index(st.session_state.selected_enquiry_id)
            except ValueError: # If ID is somehow invalid, default to first
                st.session_state.selected_enquiry_id = list(enquiry_options_tab2.values())[0]
                current_selection_index_tab2 = 0
                # Also reset states because selection was forced
                st.session_state.current_ai_suggestions = None
                st.session_state.current_ai_suggestions_id = None
                st.session_state.itinerary_loaded_for_tab2 = None


        prev_selected_enquiry_id_tab2 = st.session_state.selected_enquiry_id
        selected_enquiry_label_tab2 = st.selectbox(
            "Select an Enquiry for Itinerary Generation:",
            options=list(enquiry_options_tab2.keys()),
            index=current_selection_index_tab2,
            key="enquiry_selector_tab2"
        )

        if selected_enquiry_label_tab2: # If a selection is made
            st.session_state.selected_enquiry_id = enquiry_options_tab2[selected_enquiry_label_tab2]

        if st.session_state.selected_enquiry_id != prev_selected_enquiry_id_tab2:
            st.session_state.current_ai_suggestions = None
            st.session_state.current_ai_suggestions_id = None
            st.session_state.itinerary_loaded_for_tab2 = None # Reset flag
            st.rerun() # Rerun if selection changed

        if st.session_state.selected_enquiry_id:
            enquiry_id_tab2 = st.session_state.selected_enquiry_id
            enquiry_details_tab2, error_msg_details_tab2 = get_enquiry_by_id(enquiry_id_tab2)

            if enquiry_details_tab2:
                # Load itinerary if not already loaded for this enquiry in this tab
                if st.session_state.itinerary_loaded_for_tab2 != enquiry_id_tab2:
                    ai_suggestions_data_tab2, _ = get_itinerary_by_enquiry_id(enquiry_id_tab2)
                    if ai_suggestions_data_tab2:
                        st.session_state.current_ai_suggestions = ai_suggestions_data_tab2['itinerary_text']
                        st.session_state.current_ai_suggestions_id = ai_suggestions_data_tab2['id']
                    else:
                        st.session_state.current_ai_suggestions = None
                        st.session_state.current_ai_suggestions_id = None
                    st.session_state.itinerary_loaded_for_tab2 = enquiry_id_tab2


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
                    with st.spinner(f"Generating AI suggestions with {st.session_state.selected_ai_provider}..."):
                        suggestions_text = generate_places_suggestion_llm(
                            enquiry_details_tab2,
                            provider=st.session_state.selected_ai_provider
                        )
                        if "Error:" not in suggestions_text and "Critical error" not in suggestions_text and "OpenRouter Model Error:" not in suggestions_text:
                            new_suggestion_record, error_msg_sugg_add = add_itinerary(enquiry_id_tab2, suggestions_text)
                            if new_suggestion_record:
                                st.session_state.current_ai_suggestions = suggestions_text
                                st.session_state.current_ai_suggestions_id = new_suggestion_record['id']
                                st.session_state.itinerary_loaded_for_tab2 = enquiry_id_tab2 # Mark it as loaded for current
                                st.session_state.vendor_reply_saved_success_message = "AI Place suggestions generated and saved successfully!" # Use the success flag
                                st.rerun()
                            else:
                                st.error(f"Failed to save AI suggestions: {error_msg_sugg_add or 'Unknown error'}")
                        else:
                            st.error(suggestions_text) # Show LLM error
            elif error_msg_details_tab2:
                 st.error(f"Could not load selected enquiry details: {error_msg_details_tab2}")
            else: # Enquiry details not found (e.g., if ID was deleted)
                 st.warning("Selected enquiry details could not be loaded or enquiry not found.")
        else:
            st.info("Select an enquiry to see details and generate itinerary.")