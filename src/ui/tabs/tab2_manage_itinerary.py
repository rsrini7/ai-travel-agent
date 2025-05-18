# src/ui/tabs/tab2_manage_itinerary.py
import streamlit as st
from src.utils.supabase_utils import (
    get_enquiry_by_id, add_itinerary, get_itinerary_by_enquiry_id
)
from src.core.itinerary_generator import generate_places_suggestion_llm
from src.ui.ui_helpers import handle_enquiry_selection
# Constants for session keys are removed as per refactoring plan,
# direct attribute access on st.session_state.app_state will be used.

def _reset_tab2_states():
    st.session_state.app_state.tab2_state.current_ai_suggestions = None
    st.session_state.app_state.tab2_state.current_ai_suggestions_id = None
    st.session_state.app_state.tab2_state.itinerary_loaded_for_tab2 = None

def render_tab2():
    st.header("2. Manage Enquiries & Generate Itinerary")

    if st.session_state.app_state.operation_success_message:
        st.success(st.session_state.app_state.operation_success_message)
        st.session_state.app_state.operation_success_message = None

    active_enquiry_id_tab2, _ = handle_enquiry_selection(
        st_object=st,
        state_model_instance=st.session_state.app_state.tab2_state,
        field_name_for_selected_id="selected_enquiry_id",
        selectbox_label="Select an Enquiry for Itinerary Generation:",
        on_selection_change_callback=_reset_tab2_states,
        unique_key_prefix="tab2",
        no_enquiries_message="No enquiries found. Please submit one in the 'New Enquiry' tab."
    )

    if active_enquiry_id_tab2:
        enquiry_details_tab2, error_msg_details_tab2 = get_enquiry_by_id(active_enquiry_id_tab2)

        if enquiry_details_tab2:
            if st.session_state.app_state.tab2_state.itinerary_loaded_for_tab2 != active_enquiry_id_tab2:
                ai_suggestions_data_tab2, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab2)
                if ai_suggestions_data_tab2:
                    st.session_state.app_state.tab2_state.current_ai_suggestions = ai_suggestions_data_tab2['itinerary_text']
                    st.session_state.app_state.tab2_state.current_ai_suggestions_id = ai_suggestions_data_tab2['id']
                else:
                    st.session_state.app_state.tab2_state.current_ai_suggestions = None
                    st.session_state.app_state.tab2_state.current_ai_suggestions_id = None
                st.session_state.app_state.tab2_state.itinerary_loaded_for_tab2 = active_enquiry_id_tab2

            st.subheader(f"Details for Enquiry: {enquiry_details_tab2['destination']} (ID: {active_enquiry_id_tab2[:8]}...)")
            st.markdown(f"""
                - **Destination:** {enquiry_details_tab2['destination']}
                - **Days:** {enquiry_details_tab2['num_days']}
                - **Travelers:** {enquiry_details_tab2['traveler_count']}
                - **Trip Type:** {enquiry_details_tab2['trip_type']}
                - **Status:** {enquiry_details_tab2.get('status', 'New')}
            """)

            st.markdown("---")
            st.subheader(f"💡 AI Places/Attraction Suggestions (using {st.session_state.app_state.ai_config.selected_ai_provider})")

            current_suggestions = st.session_state.app_state.tab2_state.current_ai_suggestions
            if current_suggestions:
                with st.expander("View AI Generated Suggestions", expanded=True):
                    st.markdown(current_suggestions)
            else:
                st.caption("No AI suggestions generated yet for this enquiry.")

            if st.button(f"Generate Places Suggestions with {st.session_state.app_state.ai_config.selected_ai_provider}", key="gen_ai_suggestions_btn_tab2"):
                with st.spinner(f"Generating AI suggestions with {st.session_state.app_state.ai_config.selected_ai_provider}..."):
                    suggestions_text, error_info = generate_places_suggestion_llm(
                        enquiry_details_tab2,
                        provider=st.session_state.app_state.ai_config.selected_ai_provider
                    )
                    if suggestions_text and not error_info:
                        new_suggestion_record, error_msg_sugg_add = add_itinerary(active_enquiry_id_tab2, suggestions_text)
                        if new_suggestion_record:
                            st.session_state.app_state.tab2_state.current_ai_suggestions = suggestions_text
                            st.session_state.app_state.tab2_state.current_ai_suggestions_id = new_suggestion_record['id']
                            st.session_state.app_state.tab2_state.itinerary_loaded_for_tab2 = active_enquiry_id_tab2 
                            st.session_state.app_state.operation_success_message = "AI Place suggestions generated and saved!"
                            st.rerun()
                        else:
                            st.error(f"Failed to save AI suggestions to database: {error_msg_sugg_add or 'Unknown error'}")
                    else: 
                        err_msg_display = "Could not generate place suggestions."
                        if error_info:
                            err_msg_display = error_info.get("message", err_msg_display)
                            st.error(f"AI Error: {err_msg_display}")
                            
                            details_to_show = error_info.get("details")
                            raw_response_to_show = error_info.get("raw_response")

                            if details_to_show or raw_response_to_show :
                                with st.expander("Error Details from AI Provider"):
                                    if error_info.get("type"): st.caption(f"Error Type: {error_info.get('type')}")
                                    if error_info.get("status_code"): st.caption(f"Status Code: {error_info.get('status_code')}")
                                    if details_to_show: st.markdown(f"**Details:**\n```\n{str(details_to_show)}\n```")
                                    if raw_response_to_show: st.markdown(f"**Raw Response:**\n```\n{str(raw_response_to_show)[:1000]}\n```") # Truncate long raw responses
                        else: 
                            st.error(err_msg_display) # Fallback if error_info is somehow None
        elif error_msg_details_tab2:
            st.error(f"Could not load selected enquiry details: {error_msg_details_tab2}")
        else:
            st.warning("Selected enquiry details could not be loaded or enquiry not found.")
    else:
        pass # Message handled by handle_enquiry_selection