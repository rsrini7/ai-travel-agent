import streamlit as st
from supabase_utils import (
    add_vendor_reply,
    add_quotation, update_quotation_storage_path,
    upload_file_to_storage
)
from quotation_graph_builder import run_quotation_generation_graph
from docx_utils import convert_pdf_bytes_to_docx_bytes
import uuid
from datetime import datetime
import hashlib # Already imported in tab3_vendor_quotation, but good practice if used here standalone

# This function is already in tab3_vendor_quotation.py, if we move all cache key generation here,
# we could import it. For now, assuming it's accessible or redefined if this file becomes standalone.
# from .tab3_vendor_quotation import _generate_graph_cache_key, _reset_tab3_cache_and_outputs
# For simplicity now, we might pass cache key generation related states or have small helpers if needed.
# For this refactor, the main tab3 file will still manage _reset_tab3_cache_and_outputs directly.

def handle_vendor_reply_submit(active_enquiry_id_tab3: str, vendor_reply_text_input: str):
    """Handles the submission of the vendor reply form."""
    if not vendor_reply_text_input:
        st.error("Vendor reply text cannot be empty.")
        return

    with st.spinner("Saving vendor reply..."):
        reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
        if reply_data:
            st.session_state.operation_success_message = f"Vendor reply saved for enquiry ID: {active_enquiry_id_tab3[:8]}..."
            st.session_state.tab3_vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
            # Reset cache and local outputs as vendor reply (a key input) has changed
            st.session_state.tab3_cached_graph_output = None
            st.session_state.tab3_cache_key = None
            st.session_state.tab3_quotation_pdf_bytes = None
            st.session_state.tab3_quotation_docx_bytes = None
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()
        else:
            st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")


def _process_graph_output_and_save(
    active_enquiry_id: str,
    pdf_bytes_output: bytes,
    structured_data_dict: dict,
    file_type: str, # "PDF" or "DOCX"
    QUOTATIONS_BUCKET_NAME: str,
    docx_bytes_for_upload: bytes = None # Only for DOCX type
):
    """Helper to process graph output, upload file, and save/update DB record."""
    is_error_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
    
    if file_type == "PDF" and pdf_bytes_output and not is_error_content and len(pdf_bytes_output) > 1000:
        st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
        storage_path_for_db = None
        with st.spinner(f"Uploading PDF to cloud storage..."):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"{active_enquiry_id}/quotation_PDF_{timestamp}_{uuid.uuid4().hex[:6]}.pdf"
            storage_path_for_db, upload_err = upload_file_to_storage(QUOTATIONS_BUCKET_NAME, fn, pdf_bytes_output, "application/pdf")
        
        if upload_err:
            st.error(f"PDF generated, but failed to upload: {upload_err}")
        else:
            st.session_state.tab3_current_pdf_storage_path = storage_path_for_db

        with st.spinner("Saving PDF quotation data to database..."):
            q_data, q_error = add_quotation(
                active_enquiry_id, structured_data_dict,
                st.session_state.tab3_itinerary_info.get('id'),
                st.session_state.tab3_vendor_reply_info.get('id'),
                pdf_storage_path=storage_path_for_db,
                docx_storage_path=st.session_state.get('tab3_current_docx_storage_path') # Preserve if DOCX was already generated
            )
            if q_error:
                st.error(f"Failed to save PDF quotation data: {q_error}")
            else:
                st.session_state.tab3_current_quotation_db_id = q_data['id']
                st.session_state.operation_success_message = "Quotation PDF generated, uploaded, and data saved!"
                st.session_state.show_quotation_success_tab3 = True
                st.rerun()
        return
    
    elif file_type == "DOCX" and docx_bytes_for_upload:
        st.session_state.tab3_quotation_docx_bytes = docx_bytes_for_upload
        storage_path_for_db = None
        with st.spinner(f"Uploading DOCX to cloud storage..."):
            ts_docx = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn_docx = f"{active_enquiry_id}/quotation_DOCX_{ts_docx}_{uuid.uuid4().hex[:6]}.docx"
            storage_path_for_db, up_err_docx = upload_file_to_storage(QUOTATIONS_BUCKET_NAME, fn_docx, docx_bytes_for_upload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        if up_err_docx:
            st.error(f"DOCX generated, but failed to upload: {up_err_docx}")
        else:
            st.session_state.tab3_current_docx_storage_path = storage_path_for_db

        with st.spinner("Saving/updating DOCX quotation data..."):
            if st.session_state.get('tab3_current_quotation_db_id'):
                _, upd_err = update_quotation_storage_path(st.session_state.tab3_current_quotation_db_id, 'docx_storage_path', storage_path_for_db)
                if upd_err:
                    st.error(f"Failed to update DOCX path in DB: {upd_err}")
                else:
                    st.session_state.operation_success_message = "DOCX generated, uploaded, and DB record updated!"
                    st.rerun()
            else: # Create new record
                q_data_dx, q_err_dx = add_quotation(
                    active_enquiry_id, structured_data_dict,
                    st.session_state.tab3_itinerary_info.get('id'),
                    st.session_state.tab3_vendor_reply_info.get('id'),
                    pdf_storage_path=st.session_state.get('tab3_current_pdf_storage_path'), # Preserve if PDF was made
                    docx_storage_path=storage_path_for_db
                )
                if q_err_dx:
                    st.error(f"Failed to save DOCX quotation data: {q_err_dx}")
                else:
                    st.session_state.tab3_current_quotation_db_id = q_data_dx['id']
                    st.session_state.operation_success_message = "DOCX generated, uploaded, and new data record saved!"
                    st.rerun()
        return

    # Handle cases where PDF/DOCX generation itself failed or produced an error document
    if file_type == "PDF":
        st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Store even if it's an error PDF
        st.error("Failed to generate a valid PDF. Error PDF might be available for download.")
    elif file_type == "DOCX" and not docx_bytes_for_upload: # This implies PDF to DOCX conversion failed
         st.error("Failed to convert PDF to DOCX.")
    elif file_type == "DOCX" and is_error_content: # Underlying PDF was an error PDF
        st.error("Could not generate underlying PDF for DOCX conversion.")
        if pdf_bytes_output:
            st.download_button("Download Intermediate Error PDF", pdf_bytes_output, "Error_PDF_for_DOCX.pdf", "application/pdf", key="err_pdf_docx_action")


def handle_pdf_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str, QUOTATIONS_BUCKET_NAME: str):
    """Handles the PDF generation process."""
    st.session_state.tab3_quotation_pdf_bytes = None
    st.session_state.tab3_current_pdf_storage_path = None
    st.session_state.show_quotation_success_tab3 = False
    
    pdf_bytes_output, structured_data_dict = None, None
    itinerary_text_for_graph = st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available.")

    if st.session_state.tab3_cached_graph_output and st.session_state.tab3_cache_key == current_graph_cache_key:
        st.info("Using cached data for PDF generation.")
        pdf_bytes_output, structured_data_dict = st.session_state.tab3_cached_graph_output
    else:
        with st.spinner(f"Generating PDF data with {st.session_state.selected_ai_provider}..."):
            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
            
            pdf_bytes_output, structured_data_dict = run_quotation_generation_graph(
                current_enquiry_details_for_gen, 
                st.session_state.tab3_vendor_reply_info['text'], 
                itinerary_text_for_graph,
                st.session_state.selected_ai_provider
            )
            if structured_data_dict and not structured_data_dict.get("error") and pdf_bytes_output and not (b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output):
                st.session_state.tab3_cached_graph_output = (pdf_bytes_output, structured_data_dict)
                st.session_state.tab3_cache_key = current_graph_cache_key
                st.caption("Quotation data generated and cached.")
            else: # Clear cache on error
                st.session_state.tab3_cached_graph_output = None
                st.session_state.tab3_cache_key = None

    if structured_data_dict and not structured_data_dict.get("error"):
        _process_graph_output_and_save(active_enquiry_id_tab3, pdf_bytes_output, structured_data_dict, "PDF", QUOTATIONS_BUCKET_NAME)
    else:
        err = structured_data_dict.get('error',"Unknown error from LLM graph") if structured_data_dict else "Graph execution error"
        st.error(f"Failed to structure data for PDF: {err}")
        if structured_data_dict and structured_data_dict.get('raw_output'):
            st.expander("Raw LLM Output").text(structured_data_dict['raw_output'])
        if pdf_bytes_output: # Store error PDF for download
            st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output

def handle_docx_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str, QUOTATIONS_BUCKET_NAME: str):
    """Handles the DOCX generation process."""
    st.session_state.tab3_quotation_docx_bytes = None
    st.session_state.tab3_current_docx_storage_path = None
    
    pdf_bytes_for_docx, structured_data_dict_docx = None, None
    itinerary_text_for_graph = st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available.")

    if st.session_state.tab3_cached_graph_output and st.session_state.tab3_cache_key == current_graph_cache_key:
        st.info("Using cached data for DOCX generation.")
        pdf_bytes_for_docx, structured_data_dict_docx = st.session_state.tab3_cached_graph_output
    else:
        with st.spinner(f"Generating base data with {st.session_state.selected_ai_provider}..."):
            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
            
            pdf_bytes_for_docx, structured_data_dict_docx = run_quotation_generation_graph(
                current_enquiry_details_for_gen, 
                st.session_state.tab3_vendor_reply_info['text'], 
                itinerary_text_for_graph,
                st.session_state.selected_ai_provider
            )
            if structured_data_dict_docx and not structured_data_dict_docx.get("error") and pdf_bytes_for_docx and not (b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx):
                st.session_state.tab3_cached_graph_output = (pdf_bytes_for_docx, structured_data_dict_docx)
                st.session_state.tab3_cache_key = current_graph_cache_key
                st.caption("Quotation data generated and cached.")
            else: # Clear cache on error
                st.session_state.tab3_cached_graph_output = None
                st.session_state.tab3_cache_key = None

    if structured_data_dict_docx and not structured_data_dict_docx.get("error"):
        is_error_pdf_content_docx = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
        if pdf_bytes_for_docx and not is_error_pdf_content_docx and len(pdf_bytes_for_docx) > 1000:
            with st.spinner("Converting PDF to DOCX..."):
                docx_bytes_output = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
            
            if docx_bytes_output:
                _process_graph_output_and_save(active_enquiry_id_tab3, pdf_bytes_for_docx, structured_data_dict_docx, "DOCX", QUOTATIONS_BUCKET_NAME, docx_bytes_for_upload=docx_bytes_output)
            else: # Conversion failed
                _process_graph_output_and_save(active_enquiry_id_tab3, pdf_bytes_for_docx, structured_data_dict_docx, "DOCX", QUOTATIONS_BUCKET_NAME, docx_bytes_for_upload=None)

        else: # Underlying PDF was an error PDF or invalid
            _process_graph_output_and_save(active_enquiry_id_tab3, pdf_bytes_for_docx, structured_data_dict_docx, "DOCX", QUOTATIONS_BUCKET_NAME, docx_bytes_for_upload=None)
            
    else: # Error in structuring data for DOCX
        err_dx = structured_data_dict_docx.get('error',"Unknown error from LLM graph") if structured_data_dict_docx else "Graph execution error"
        st.error(f"Failed to structure data for DOCX: {err_dx}")
        if structured_data_dict_docx and structured_data_dict_docx.get('raw_output'):
            st.expander("Raw LLM Output (DOCX)").text(structured_data_dict_docx['raw_output'])