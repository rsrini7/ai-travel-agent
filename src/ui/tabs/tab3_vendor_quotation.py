import streamlit as st
from src.utils.supabase_utils import (
    get_enquiry_by_id, get_client_by_enquiry_id,
    get_vendor_reply_by_enquiry_id,
    get_itinerary_by_enquiry_id,
    get_quotation_by_enquiry_id
)
import hashlib
from src.ui.ui_helpers import handle_enquiry_selection # Import the helper
from src.utils.constants import ( # Import relevant session keys and bucket name
    BUCKET_QUOTATIONS,
    SESSION_KEY_TAB3_SELECTED_ENQUIRY_ID,
    SESSION_KEY_OPERATION_SUCCESS_MESSAGE
)

from src.ui.components.tab3_ui_components import (
    display_enquiry_and_itinerary_details_tab3,
    render_vendor_reply_section,
    render_quotation_generation_section,
    display_quotation_files_section
)
from src.ui.components.tab3_actions import (
    handle_vendor_reply_submit,
    handle_pdf_generation,
    handle_docx_generation
)

def _generate_graph_cache_key(enquiry_id: str, client_name: str, vendor_reply_text: str, ai_itinerary_text: str, llm_provider: str, llm_model: str | None) -> str:
    key_string = f"{enquiry_id}-{client_name}-{vendor_reply_text}-{ai_itinerary_text}-{llm_provider}-{llm_model or 'N/A'}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

def _reset_tab3_specific_data_on_selection_change():
    """Callback to reset tab3 specific states when enquiry selection changes."""
    st.session_state.tab3_enquiry_details = None
    st.session_state.tab3_client_name = "Valued Client" # Reset to default
    st.session_state.tab3_itinerary_info = None
    st.session_state.tab3_vendor_reply_info = None
    
    # Quotation graph cache and outputs
    st.session_state.tab3_cached_graph_output = None
    st.session_state.tab3_cache_key = None
    st.session_state.tab3_quotation_pdf_bytes = None
    st.session_state.tab3_quotation_docx_bytes = None
    
    # Quotation DB record info for current enquiry
    st.session_state.tab3_current_quotation_db_id = None
    st.session_state.tab3_current_pdf_storage_path = None
    st.session_state.tab3_current_docx_storage_path = None
    
    st.session_state.show_quotation_success_tab3 = False


def render_tab3(QUOTATIONS_BUCKET_NAME_param: str): # Param remains for flexibility if needed outside constant
    # QUOTATIONS_BUCKET_NAME = QUOTATIONS_BUCKET_NAME_param # Use param
    # OR:
    # from constants import BUCKET_QUOTATIONS # Use constant directly, param becomes redundant
    # For this refactor, let's assume the param is the way it's passed, consistent with app.py
    # However, if BUCKET_QUOTATIONS is always the same, importing from constants is cleaner.
    # Let's stick to the existing param passing for now to minimize app.py changes.
    # So, `tab3_actions` will import `BUCKET_QUOTATIONS` from `constants`
    # and `tab3_ui_components` will receive it as a parameter if it needs it.

    st.header("3. Add Vendor Reply & Generate Quotation")

    if st.session_state.get(SESSION_KEY_OPERATION_SUCCESS_MESSAGE):
        st.success(st.session_state[SESSION_KEY_OPERATION_SUCCESS_MESSAGE])
        st.session_state[SESSION_KEY_OPERATION_SUCCESS_MESSAGE] = None

    active_enquiry_id_tab3, _ = handle_enquiry_selection(
        st_object=st,
        session_state_key_for_selected_id=SESSION_KEY_TAB3_SELECTED_ENQUIRY_ID,
        selectbox_label="Select Enquiry:",
        on_selection_change_callback=_reset_tab3_specific_data_on_selection_change,
        no_enquiries_message="No enquiries available. Submit one in 'New Enquiry' tab."
    )

    if active_enquiry_id_tab3:
        # Load/Refresh data if enquiry details are not loaded or enquiry ID changed (handled by callback now)
        # The callback _reset_tab3_specific_data_on_selection_change ensures states are None'd out.
        # We load them here if they are None.
        
        if st.session_state.tab3_enquiry_details is None: # Indicates a change or first load
            details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
            st.session_state.tab3_enquiry_details = details

            client_data, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
            st.session_state.tab3_client_name = client_data["name"] if client_data and client_data.get("name") else "Valued Client"
            
            vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
            st.session_state.tab3_vendor_reply_info = {
                'text': vendor_reply_data['reply_text'] if vendor_reply_data else None, 
                'id': vendor_reply_data['id'] if vendor_reply_data else None
            }
            
            latest_quotation_rec, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
            if latest_quotation_rec:
                st.session_state.tab3_current_quotation_db_id = latest_quotation_rec.get('id')
                st.session_state.tab3_current_pdf_storage_path = latest_quotation_rec.get('pdf_storage_path')
                st.session_state.tab3_current_docx_storage_path = latest_quotation_rec.get('docx_storage_path')
            else:
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
            # Cache is already reset by the callback

        # Always refresh itinerary text from DB and check if it changed, invalidating cache if so
        # This part needs to be inside the `if active_enquiry_id_tab3:` block
        itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
        new_itinerary_text = itinerary_data_tab3['itinerary_text'] if itinerary_data_tab3 else "No AI-generated itinerary/suggestions available. Please generate in Tab 2."
        
        # If itinerary text itself changes for the *same* selected enquiry, invalidate cache
        if st.session_state.tab3_itinerary_info is None or \
           st.session_state.tab3_itinerary_info.get('text') != new_itinerary_text:
            st.session_state.tab3_cached_graph_output = None # Itinerary changed, invalidate cache
            st.session_state.tab3_cache_key = None

        st.session_state.tab3_itinerary_info = {
            'text': new_itinerary_text,
            'id': itinerary_data_tab3['id'] if itinerary_data_tab3 else None
        }
        
        # Ensure enquiry details are loaded before proceeding
        if not st.session_state.tab3_enquiry_details:
            st.warning("Loading enquiry details...") # Should be brief as data is fetched above
            st.rerun() # Rerun to ensure details are processed

        display_enquiry_and_itinerary_details_tab3(active_enquiry_id_tab3)
        render_vendor_reply_section(active_enquiry_id_tab3, handle_vendor_reply_submit)
        
        if st.session_state.tab3_enquiry_details and st.session_state.tab3_vendor_reply_info:
            current_graph_cache_key = _generate_graph_cache_key(
                active_enquiry_id_tab3,
                st.session_state.tab3_client_name,
                st.session_state.tab3_vendor_reply_info.get('text', ""),
                st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available."),
                st.session_state.selected_ai_provider,
                st.session_state.get('selected_model_for_provider')
            )

            render_quotation_generation_section(
                active_enquiry_id_tab3,
                lambda aid, ckey: handle_pdf_generation(aid, ckey), 
                lambda aid, ckey: handle_docx_generation(aid, ckey),
                current_graph_cache_key
            )

        # Pass BUCKET_QUOTATIONS (from constants) to the display function
        display_quotation_files_section(active_enquiry_id_tab3, BUCKET_QUOTATIONS) 

    else:
        # This message is now handled by handle_enquiry_selection if enquiries_list is empty
        # st.info("Select an enquiry to manage its vendor reply and quotation.")
        pass