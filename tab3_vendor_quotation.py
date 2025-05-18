import streamlit as st
from supabase_utils import (
    get_enquiries, get_enquiry_by_id, get_client_by_enquiry_id,
    get_vendor_reply_by_enquiry_id,
    get_itinerary_by_enquiry_id,
    get_quotation_by_enquiry_id
)
import hashlib

# Import new helper modules
from tab3_ui_components import (
    display_enquiry_and_itinerary_details_tab3,
    render_vendor_reply_section,
    render_quotation_generation_section,
    display_quotation_files_section
)
from tab3_actions import (
    handle_vendor_reply_submit,
    handle_pdf_generation,
    handle_docx_generation
)

def _generate_graph_cache_key(enquiry_id: str, client_name: str, vendor_reply_text: str, ai_itinerary_text: str, llm_provider: str, llm_model: str | None) -> str:
    """Generates a unique key for caching quotation graph inputs."""
    key_string = f"{enquiry_id}-{client_name}-{vendor_reply_text}-{ai_itinerary_text}-{llm_provider}-{llm_model or 'N/A'}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

def _reset_tab3_cache_and_outputs():
    """Resets cache and locally generated file bytes for Tab 3."""
    st.session_state.tab3_cached_graph_output = None
    st.session_state.tab3_cache_key = None
    st.session_state.tab3_quotation_pdf_bytes = None
    st.session_state.tab3_quotation_docx_bytes = None

def render_tab3(QUOTATIONS_BUCKET_NAME_param: str):
    QUOTATIONS_BUCKET_NAME = QUOTATIONS_BUCKET_NAME_param

    st.header("3. Add Vendor Reply & Generate Quotation")

    if st.session_state.get('operation_success_message'):
        st.success(st.session_state.operation_success_message)
        st.session_state.operation_success_message = None

    enquiries_list_tab3, error_msg_enq_list_tab3 = get_enquiries()
    if error_msg_enq_list_tab3:
        st.error(f"Could not load enquiries: {error_msg_enq_list_tab3}")
        enquiries_list_tab3 = []

    if not enquiries_list_tab3:
        st.info("No enquiries available. Submit one in 'New Enquiry' tab.")
        if st.session_state.get('selected_enquiry_id_tab3') is not None: # Only reset if there was a selection
            st.session_state.selected_enquiry_id_tab3 = None
            _reset_tab3_cache_and_outputs()
            st.session_state.tab3_enquiry_details = None
            st.session_state.tab3_current_quotation_db_id = None
            st.session_state.tab3_current_pdf_storage_path = None
            st.session_state.tab3_current_docx_storage_path = None
    else:
        enquiry_options_tab3 = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_list_tab3}

        # Initialize selected_enquiry_id_tab3 if it's not set or invalid
        if 'selected_enquiry_id_tab3' not in st.session_state or \
           st.session_state.selected_enquiry_id_tab3 not in enquiry_options_tab3.values():
            st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0] if enquiry_options_tab3 else None
            # If selection was forced, reset dependent states
            if st.session_state.selected_enquiry_id_tab3:
                st.session_state.tab3_enquiry_details = None # Force reload of details
                _reset_tab3_cache_and_outputs()
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
                st.session_state.show_quotation_success_tab3 = False


        current_selection_index_tab3 = 0
        if st.session_state.selected_enquiry_id_tab3 and enquiry_options_tab3:
            try:
                current_selection_index_tab3 = list(enquiry_options_tab3.values()).index(st.session_state.selected_enquiry_id_tab3)
            except ValueError: # Should be caught by above block, but as a safeguard
                st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0]
                current_selection_index_tab3 = 0
                st.session_state.tab3_enquiry_details = None
                _reset_tab3_cache_and_outputs()
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
                st.session_state.show_quotation_success_tab3 = False


        prev_selected_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3
        selected_enquiry_label_tab3 = st.selectbox(
            "Select Enquiry:",
            options=list(enquiry_options_tab3.keys()),
            index=current_selection_index_tab3,
            key="enquiry_selector_tab3"
        )

        if selected_enquiry_label_tab3: # Ensure a selection is made
            st.session_state.selected_enquiry_id_tab3 = enquiry_options_tab3[selected_enquiry_label_tab3]

        if st.session_state.selected_enquiry_id_tab3 != prev_selected_enquiry_id_tab3:
            st.session_state.tab3_enquiry_details = None # Force reload of details for new selection
            _reset_tab3_cache_and_outputs()
            st.session_state.tab3_current_quotation_db_id = None
            st.session_state.tab3_current_pdf_storage_path = None
            st.session_state.tab3_current_docx_storage_path = None
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            # Load/Refresh data if enquiry details are not loaded or enquiry ID changed
            if st.session_state.tab3_enquiry_details is None or \
               st.session_state.tab3_enquiry_details.get('id') != active_enquiry_id_tab3:
                details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
                st.session_state.tab3_enquiry_details = details

                client_data, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_client_name = client_data["name"] if client_data and client_data.get("name") else "Valued Client"
                
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_vendor_reply_info = {'text': vendor_reply_data['reply_text'] if vendor_reply_data else None, 'id': vendor_reply_data['id'] if vendor_reply_data else None}
                
                latest_quotation_rec, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
                if latest_quotation_rec:
                    st.session_state.tab3_current_quotation_db_id = latest_quotation_rec.get('id')
                    st.session_state.tab3_current_pdf_storage_path = latest_quotation_rec.get('pdf_storage_path')
                    st.session_state.tab3_current_docx_storage_path = latest_quotation_rec.get('docx_storage_path')
                else: # No existing quotation record for this enquiry
                    st.session_state.tab3_current_quotation_db_id = None
                    st.session_state.tab3_current_pdf_storage_path = None
                    st.session_state.tab3_current_docx_storage_path = None
                _reset_tab3_cache_and_outputs() # Essential to reset cache when new enquiry data is loaded


            # Always refresh itinerary text from DB and check if it changed, invalidating cache if so
            itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
            new_itinerary_text = itinerary_data_tab3['itinerary_text'] if itinerary_data_tab3 else "No AI-generated itinerary/suggestions available. Please generate in Tab 2."
            
            if 'tab3_itinerary_info' not in st.session_state or st.session_state.tab3_itinerary_info is None or \
               st.session_state.tab3_itinerary_info.get('text') != new_itinerary_text:
                _reset_tab3_cache_and_outputs() # Itinerary changed, invalidate cache

            st.session_state.tab3_itinerary_info = {
                'text': new_itinerary_text,
                'id': itinerary_data_tab3['id'] if itinerary_data_tab3 else None
            }
            
            # Display section for enquiry and itinerary
            display_enquiry_and_itinerary_details_tab3(active_enquiry_id_tab3)

            # Vendor Reply Section
            render_vendor_reply_section(active_enquiry_id_tab3, handle_vendor_reply_submit)
            
            # Quotation Generation Section
            # Ensure all inputs for cache key are available
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
                    lambda aid, ckey: handle_pdf_generation(aid, ckey, QUOTATIONS_BUCKET_NAME), # Pass bucket name
                    lambda aid, ckey: handle_docx_generation(aid, ckey, QUOTATIONS_BUCKET_NAME),# Pass bucket name
                    current_graph_cache_key
                )

            # Download/View Files Section
            display_quotation_files_section(active_enquiry_id_tab3, QUOTATIONS_BUCKET_NAME)

        else: # No enquiry selected (should only happen if enquiries_list_tab3 is empty initially)
            st.info("Select an enquiry to manage its vendor reply and quotation.")