import streamlit as st
import hashlib

from src.utils.supabase_utils import (
    get_enquiry_by_id, get_client_by_enquiry_id,
    get_vendor_reply_by_enquiry_id,
    get_itinerary_by_enquiry_id,
    get_quotation_by_enquiry_id
)
import hashlib
from src.ui.ui_helpers import handle_enquiry_selection
# SESSION_KEY constants removed as per refactoring plan

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

def _generate_graph_cache_key(
    enquiry_id: str, 
    client_name: str, 
    vendor_reply_text: str, 
    ai_itinerary_text: str, 
    llm_provider: str, 
    llm_model: str | None,
    temperature: float | None, # New
    max_tokens: int | None # New
) -> str:
    key_string = (
        f"{enquiry_id}-{client_name}-{vendor_reply_text}-{ai_itinerary_text}-"
        f"{llm_provider}-{llm_model or 'N/A'}-"
        f"temp:{temperature if temperature is not None else AIConfigState().temperature}-" # Use default from model if None for consistent key
        f"maxtok:{max_tokens if max_tokens is not None else 'provider_default'}" 
    )
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

def _reset_tab3_specific_data_on_selection_change():
    """Callback to reset tab3 specific states when enquiry selection changes."""
    st.session_state.app_state.tab3_state.enquiry_details = None
    st.session_state.app_state.tab3_state.client_name = "Valued Client" # Reset to default
    st.session_state.app_state.tab3_state.itinerary_info = None
    st.session_state.app_state.tab3_state.vendor_reply_info = None
    
    # Quotation graph cache and outputs
    st.session_state.app_state.tab3_state.cached_graph_output = None
    st.session_state.app_state.tab3_state.cache_key = None
    st.session_state.app_state.tab3_state.quotation_pdf_bytes = None
    st.session_state.app_state.tab3_state.quotation_docx_bytes = None
    
    # Quotation DB record info for current enquiry
    st.session_state.app_state.tab3_state.current_quotation_db_id = None
    st.session_state.app_state.tab3_state.current_pdf_storage_path = None
    st.session_state.app_state.tab3_state.current_docx_storage_path = None
    
    st.session_state.app_state.tab3_state.show_quotation_success = False


def render_tab3(): 
    """Render the UI for the 'Add Vendor Reply & Generate Quotation' tab."""
    
    st.header("3. Add Vendor Reply & Generate Quotation")

    if st.session_state.app_state.operation_success_message:
        st.success(st.session_state.app_state.operation_success_message)
        st.session_state.app_state.operation_success_message = None

    active_enquiry_id_tab3, _ = handle_enquiry_selection(
        st_object=st,
        state_model_instance=st.session_state.app_state.tab3_state,
        field_name_for_selected_id="selected_enquiry_id",
        selectbox_label="Select Enquiry:",
        on_selection_change_callback=_reset_tab3_specific_data_on_selection_change,
        unique_key_prefix="tab3",
        no_enquiries_message="No enquiries available. Submit one in 'New Enquiry' tab."
    )

    if active_enquiry_id_tab3:
        # Load/Refresh data if enquiry details are not loaded or enquiry ID changed (handled by callback now)
        # The callback _reset_tab3_specific_data_on_selection_change ensures states are None'd out.
        # We load them here if they are None.
        
        if st.session_state.app_state.tab3_state.enquiry_details is None: # Indicates a change or first load
            details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
            st.session_state.app_state.tab3_state.enquiry_details = details

            client_data, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
            st.session_state.app_state.tab3_state.client_name = client_data["name"] if client_data and client_data.get("name") else "Valued Client"
            
            vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
            st.session_state.app_state.tab3_state.vendor_reply_info = {
                'text': vendor_reply_data['reply_text'] if vendor_reply_data else None, 
                'id': vendor_reply_data['id'] if vendor_reply_data else None
            }
            
            latest_quotation_rec, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
            if latest_quotation_rec:
                st.session_state.app_state.tab3_state.current_quotation_db_id = latest_quotation_rec.get('id')
                st.session_state.app_state.tab3_state.current_pdf_storage_path = latest_quotation_rec.get('pdf_storage_path')
                st.session_state.app_state.tab3_state.current_docx_storage_path = latest_quotation_rec.get('docx_storage_path')
            else:
                st.session_state.app_state.tab3_state.current_quotation_db_id = None
                st.session_state.app_state.tab3_state.current_pdf_storage_path = None
                st.session_state.app_state.tab3_state.current_docx_storage_path = None
            # Cache is already reset by the callback

        # Always refresh itinerary text from DB and check if it changed, invalidating cache if so
        # This part needs to be inside the `if active_enquiry_id_tab3:` block
        itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
        new_itinerary_text = itinerary_data_tab3['itinerary_text'] if itinerary_data_tab3 else "No AI-generated itinerary/suggestions available. Please generate in Tab 2."
        
        # If itinerary text itself changes for the *same* selected enquiry, invalidate cache
        if st.session_state.app_state.tab3_state.itinerary_info is None or \
           st.session_state.app_state.tab3_state.itinerary_info.get('text') != new_itinerary_text:
            st.session_state.app_state.tab3_state.cached_graph_output = None # Itinerary changed, invalidate cache
            st.session_state.app_state.tab3_state.cache_key = None

        st.session_state.app_state.tab3_state.itinerary_info = {
            'text': new_itinerary_text,
            'id': itinerary_data_tab3['id'] if itinerary_data_tab3 else None
        }
        
        # Ensure enquiry details are loaded before proceeding
        if not st.session_state.app_state.tab3_state.enquiry_details:
            st.warning("Loading enquiry details...") # Should be brief as data is fetched above
            st.rerun() # Rerun to ensure details are processed

        display_enquiry_and_itinerary_details_tab3(active_enquiry_id_tab3)
        render_vendor_reply_section(active_enquiry_id_tab3, handle_vendor_reply_submit)
        
        if st.session_state.app_state.tab3_state.enquiry_details and st.session_state.app_state.tab3_state.vendor_reply_info:
            ai_conf_for_key = st.session_state.app_state.ai_config # Get current AI config
            current_graph_cache_key = _generate_graph_cache_key(
                active_enquiry_id_tab3,
                st.session_state.app_state.tab3_state.client_name,
                st.session_state.app_state.tab3_state.vendor_reply_info.get('text', ""),
                st.session_state.app_state.tab3_state.itinerary_info.get('text', "Itinerary suggestions not available."),
                ai_conf_for_key.selected_ai_provider,
                ai_conf_for_key.selected_model_for_provider,
                ai_conf_for_key.temperature,   # Pass current temperature
                ai_conf_for_key.max_tokens     # Pass current max_tokens
            )

            render_quotation_generation_section(
                active_enquiry_id_tab3,
                lambda aid, ckey: handle_pdf_generation(aid, ckey), 
                lambda aid, ckey: handle_docx_generation(aid, ckey),
                current_graph_cache_key
            )
            
        display_quotation_files_section(active_enquiry_id_tab3) 

    else:
        # This message is now handled by handle_enquiry_selection if enquiries_list is empty
        # st.info("Select an enquiry to manage its vendor reply and quotation.")
        pass