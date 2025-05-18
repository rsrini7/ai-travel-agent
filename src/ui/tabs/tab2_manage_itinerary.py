import streamlit as st
from src.utils.supabase_utils import (
    get_enquiry_by_id, add_itinerary, get_itinerary_by_enquiry_id
)
from src.core.itinerary_generator import generate_places_suggestion_llm
from src.ui.ui_helpers import handle_enquiry_selection
from src.utils.constants import ( # Import relevant session keys
    SESSION_KEY_TAB2_SELECTED_ENQUIRY_ID,
    SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS,
    SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID,
    SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG,
    SESSION_KEY_OPERATION_SUCCESS_MESSAGE
)

def _reset_tab2_states():
    """Callback to reset tab2 specific states when enquiry selection changes."""
    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS] = None
    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID] = None
    st.session_state[SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG] = None

def render_tab2():
    st.header("2. Manage Enquiries & Generate Itinerary")

    if st.session_state.get(SESSION_KEY_OPERATION_SUCCESS_MESSAGE):
        st.success(st.session_state[SESSION_KEY_OPERATION_SUCCESS_MESSAGE])
        st.session_state[SESSION_KEY_OPERATION_SUCCESS_MESSAGE] = None

    # Use the new helper for enquiry selection
    active_enquiry_id_tab2, _ = handle_enquiry_selection(
        st_object=st,
        session_state_key_for_selected_id=SESSION_KEY_TAB2_SELECTED_ENQUIRY_ID,
        selectbox_label="Select an Enquiry for Itinerary Generation:",
        on_selection_change_callback=_reset_tab2_states,
        no_enquiries_message="No enquiries found. Please submit one in the 'New Enquiry' tab."
    )

    if active_enquiry_id_tab2:
        enquiry_details_tab2, error_msg_details_tab2 = get_enquiry_by_id(active_enquiry_id_tab2)

        if enquiry_details_tab2:
            # Load itinerary if not loaded for current enquiry or if flag isn't set
            if st.session_state.get(SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG) != active_enquiry_id_tab2:
                ai_suggestions_data_tab2, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab2)
                if ai_suggestions_data_tab2:
                    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS] = ai_suggestions_data_tab2['itinerary_text']
                    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID] = ai_suggestions_data_tab2['id']
                else:
                    # _reset_tab2_states would have cleared these, but good to be explicit if needed
                    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS] = None
                    st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID] = None
                st.session_state[SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG] = active_enquiry_id_tab2

            st.subheader(f"Details for Enquiry: {enquiry_details_tab2['destination']} (ID: {active_enquiry_id_tab2[:8]}...)")
            st.markdown(f"""
                - **Destination:** {enquiry_details_tab2['destination']}
                - **Days:** {enquiry_details_tab2['num_days']}
                - **Travelers:** {enquiry_details_tab2['traveler_count']}
                - **Trip Type:** {enquiry_details_tab2['trip_type']}
                - **Status:** {enquiry_details_tab2.get('status', 'New')}
            """)

            st.markdown("---")
            st.subheader(f"💡 AI Places/Attraction Suggestions (using {st.session_state.selected_ai_provider})")

            current_suggestions = st.session_state.get(SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS)
            if current_suggestions:
                with st.expander("View AI Generated Suggestions", expanded=True):
                    st.markdown(current_suggestions)
            else:
                st.caption("No AI suggestions generated yet for this enquiry.")

            if st.button(f"Generate Places Suggestions with {st.session_state.selected_ai_provider}", key="gen_ai_suggestions_btn_tab2"):
                with st.spinner(f"Generating AI suggestions with {st.session_state.selected_ai_provider}..."):
                    suggestions_text = generate_places_suggestion_llm(
                        enquiry_details_tab2,
                        provider=st.session_state.selected_ai_provider
                    )
                    if "Error:" not in suggestions_text and "Critical error" not in suggestions_text and "OpenRouter Model Error:" not in suggestions_text:
                        new_suggestion_record, error_msg_sugg_add = add_itinerary(active_enquiry_id_tab2, suggestions_text)
                        if new_suggestion_record:
                            st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS] = suggestions_text
                            st.session_state[SESSION_KEY_TAB2_CURRENT_AI_SUGGESTIONS_ID] = new_suggestion_record['id']
                            st.session_state[SESSION_KEY_TAB2_ITINERARY_LOADED_FLAG] = active_enquiry_id_tab2 # Mark as loaded
                            st.session_state[SESSION_KEY_OPERATION_SUCCESS_MESSAGE] = "AI Place suggestions generated and saved successfully!"
                            st.rerun()
                        else:
                            st.error(f"Failed to save AI suggestions: {error_msg_sugg_add or 'Unknown error'}")
                    else:
                        st.error(suggestions_text)
        elif error_msg_details_tab2:
            st.error(f"Could not load selected enquiry details: {error_msg_details_tab2}")
        else:
            st.warning("Selected enquiry details could not be loaded or enquiry not found.")
    else:
        # This message is now handled by handle_enquiry_selection if enquiries_list is empty
        # st.info("Select an enquiry to see details and generate itinerary.")
        pass