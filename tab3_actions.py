# tab3_actions.py
import streamlit as st
from supabase_utils import (
    add_vendor_reply,
    add_quotation, update_quotation_storage_path,
    upload_file_to_storage
)
from quotation_graph_builder import run_quotation_generation_graph
from docx_utils import convert_pdf_bytes_to_docx_bytes
from constants import BUCKET_QUOTATIONS # Import constant
import uuid
from datetime import datetime
import hashlib

def handle_vendor_reply_submit(active_enquiry_id_tab3: str, vendor_reply_text_input: str):
    if not vendor_reply_text_input:
        st.error("Vendor reply text cannot be empty.")
        return

    with st.spinner("Saving vendor reply..."):
        reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
        if reply_data:
            st.session_state.operation_success_message = f"Vendor reply saved for enquiry ID: {active_enquiry_id_tab3[:8]}..."
            st.session_state.tab3_vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
            st.session_state.tab3_cached_graph_output = None
            st.session_state.tab3_cache_key = None
            st.session_state.tab3_quotation_pdf_bytes = None
            st.session_state.tab3_quotation_docx_bytes = None
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()
        else:
            st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")

# --- Refactored Helper Functions for PDF/DOCX processing ---
def _handle_pdf_processing_and_storage(
    active_enquiry_id: str,
    pdf_bytes_output: bytes,
    structured_data_dict: dict,
    is_error_content_in_pdf: bool
):
    """Handles PDF specific processing: storage, DB update, session state."""
    if pdf_bytes_output and not is_error_content_in_pdf and len(pdf_bytes_output) > 1000: # Basic validity check
        st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
        storage_path_for_db = None
        with st.spinner("Uploading PDF to cloud storage..."):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"{active_enquiry_id}/quotation_PDF_{timestamp}_{uuid.uuid4().hex[:6]}.pdf"
            storage_path_for_db, upload_err = upload_file_to_storage(
                BUCKET_QUOTATIONS, fn, pdf_bytes_output, "application/pdf"
            )
        
        if upload_err:
            st.error(f"PDF generated, but failed to upload: {upload_err}")
            # PDF bytes are already in session state for local download
        else:
            st.session_state.tab3_current_pdf_storage_path = storage_path_for_db

        with st.spinner("Saving PDF quotation data to database..."):
            # If a DOCX was generated in a previous step of THIS SAME overall quotation generation flow (unlikely but covering state)
            # it would be in st.session_state.tab3_current_docx_storage_path.
            # However, typically PDF is generated first, then DOCX if requested, updating the same record.
            q_data, q_error = add_quotation(
                enquiry_id=active_enquiry_id,
                structured_data_json=structured_data_dict,
                itinerary_used_id=st.session_state.tab3_itinerary_info.get('id'),
                vendor_reply_used_id=st.session_state.tab3_vendor_reply_info.get('id'),
                pdf_storage_path=storage_path_for_db,
                docx_storage_path=st.session_state.get('tab3_current_docx_storage_path') # Preserve if DOCX existed from a *prior* generation
            )
            if q_error:
                st.error(f"Failed to save PDF quotation data: {q_error}")
            else:
                st.session_state.tab3_current_quotation_db_id = q_data['id']
                if not upload_err: # Only show full success if upload also worked
                    st.session_state.operation_success_message = "Quotation PDF generated, uploaded, and data saved!"
                else:
                    st.session_state.operation_success_message = "Quotation PDF generated and data saved (upload failed)."
                st.session_state.show_quotation_success_tab3 = True
                st.rerun() # Rerun to reflect new state (e.g., download links)
    else:
        st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Store error PDF for download
        st.error("Failed to generate a valid PDF. Error PDF might be available for download.")
        st.session_state.show_quotation_success_tab3 = False


def _handle_docx_processing_and_storage(
    active_enquiry_id: str,
    docx_bytes_for_upload: bytes | None, # Actual DOCX bytes
    structured_data_dict: dict, # From the graph (same as for PDF)
    is_error_content_in_original_pdf: bool, # Info about the source PDF
    source_pdf_bytes: bytes # The PDF from which DOCX was (or was attempted to be) converted
):
    """Handles DOCX specific processing: storage, DB update, session state."""
    if docx_bytes_for_upload: # DOCX conversion was successful
        st.session_state.tab3_quotation_docx_bytes = docx_bytes_for_upload
        storage_path_for_db_docx = None

        with st.spinner("Uploading DOCX to cloud storage..."):
            ts_docx = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn_docx = f"{active_enquiry_id}/quotation_DOCX_{ts_docx}_{uuid.uuid4().hex[:6]}.docx"
            storage_path_for_db_docx, up_err_docx = upload_file_to_storage(
                BUCKET_QUOTATIONS, fn_docx, docx_bytes_for_upload, 
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        if up_err_docx:
            st.error(f"DOCX generated, but failed to upload: {up_err_docx}")
        else:
            st.session_state.tab3_current_docx_storage_path = storage_path_for_db_docx
        
        with st.spinner("Saving/updating DOCX quotation data..."):
            # Check if a PDF was already generated and a record exists
            existing_quotation_id = st.session_state.get('tab3_current_quotation_db_id')
            
            if existing_quotation_id:
                _, upd_err = update_quotation_storage_path(
                    existing_quotation_id, 'docx_storage_path', storage_path_for_db_docx
                )
                if upd_err:
                    st.error(f"Failed to update DOCX path in DB: {upd_err}")
                else:
                    if not up_err_docx:
                        st.session_state.operation_success_message = "DOCX generated, uploaded, and DB record updated!"
                    else:
                         st.session_state.operation_success_message = "DOCX generated and DB record updated (upload failed)!"
                    st.rerun()
            else: # No existing record, create a new one (PDF might not have been generated/saved successfully before)
                q_data_dx, q_err_dx = add_quotation(
                    active_enquiry_id, structured_data_dict,
                    st.session_state.tab3_itinerary_info.get('id'),
                    st.session_state.tab3_vendor_reply_info.get('id'),
                    pdf_storage_path=st.session_state.get('tab3_current_pdf_storage_path'), # Preserve if PDF was somehow made
                    docx_storage_path=storage_path_for_db_docx
                )
                if q_err_dx:
                    st.error(f"Failed to save new DOCX quotation data: {q_err_dx}")
                else:
                    st.session_state.tab3_current_quotation_db_id = q_data_dx['id']
                    if not up_err_docx:
                        st.session_state.operation_success_message = "DOCX generated, uploaded, and new data record saved!"
                    else:
                        st.session_state.operation_success_message = "DOCX generated and new data record saved (upload failed)!"
                    st.rerun()
        st.session_state.show_quotation_success_tab3 = True

    else: # DOCX conversion failed or original PDF was an error doc
        st.session_state.tab3_quotation_docx_bytes = None # No valid DOCX bytes
        if is_error_content_in_original_pdf:
            st.error("Could not generate DOCX because the underlying PDF data was an error document.")
            if source_pdf_bytes: # The error PDF from graph
                st.download_button(
                    "Download Intermediate Error PDF", source_pdf_bytes, 
                    f"Error_PDF_for_DOCX_{active_enquiry_id[:4]}.pdf", "application/pdf", 
                    key="err_pdf_docx_action_dl"
                )
        else:
            st.error("Failed to convert PDF to DOCX.")
        st.session_state.show_quotation_success_tab3 = False


# --- Main PDF/DOCX Generation Triggers ---
def handle_pdf_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str):
    st.session_state.tab3_quotation_pdf_bytes = None
    st.session_state.tab3_current_pdf_storage_path = None # Reset before new generation
    # Do not reset tab3_current_quotation_db_id here, as PDF generation might add to an existing record if DOCX was done first (unlikely flow but safer)
    # Or, if PDF is always first, then this is fine. Let's assume PDF can be regen, so DB ID might need update or new.
    # The add_quotation / update_quotation logic inside helpers handles this.
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
            is_graph_error = structured_data_dict and structured_data_dict.get("error") or \
                             not pdf_bytes_output or \
                             (b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output)

            if not is_graph_error:
                st.session_state.tab3_cached_graph_output = (pdf_bytes_output, structured_data_dict)
                st.session_state.tab3_cache_key = current_graph_cache_key
                st.caption("Quotation data generated and cached.")
            else: 
                st.session_state.tab3_cached_graph_output = None
                st.session_state.tab3_cache_key = None
                st.error(f"Error from quotation graph: {structured_data_dict.get('error', 'Unknown graph error')}")
                if structured_data_dict and structured_data_dict.get('raw_output'):
                    st.expander("Raw LLM Output").text(structured_data_dict['raw_output'])
                # Store error PDF if available
                if pdf_bytes_output: st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                return # Stop processing

    # Proceed if graph output (cached or new) is available and seems okay
    if pdf_bytes_output and structured_data_dict and not structured_data_dict.get("error"):
        is_error_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
        _handle_pdf_processing_and_storage(
            active_enquiry_id_tab3, pdf_bytes_output, structured_data_dict, is_error_content
        )
    elif structured_data_dict and structured_data_dict.get("error"): # Error from graph structuring even if PDF bytes exist
        st.error(f"Failed to structure data for PDF: {structured_data_dict.get('error')}")
        if structured_data_dict.get('raw_output'):
            st.expander("Raw LLM Output").text(structured_data_dict['raw_output'])
        if pdf_bytes_output: # Store error PDF for download
            st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output


def handle_docx_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str):
    st.session_state.tab3_quotation_docx_bytes = None
    st.session_state.tab3_current_docx_storage_path = None # Reset before new generation
    st.session_state.show_quotation_success_tab3 = False
    
    pdf_bytes_for_docx, structured_data_dict_docx = None, None # These are from the graph
    itinerary_text_for_graph = st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available.")

    # Step 1: Get PDF and Structured Data (from cache or new graph run)
    if st.session_state.tab3_cached_graph_output and st.session_state.tab3_cache_key == current_graph_cache_key:
        st.info("Using cached data for DOCX generation.")
        pdf_bytes_for_docx, structured_data_dict_docx = st.session_state.tab3_cached_graph_output
    else:
        with st.spinner(f"Generating base data with {st.session_state.selected_ai_provider}... (for DOCX)"):
            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
            
            pdf_bytes_for_docx, structured_data_dict_docx = run_quotation_generation_graph(
                current_enquiry_details_for_gen, 
                st.session_state.tab3_vendor_reply_info['text'], 
                itinerary_text_for_graph,
                st.session_state.selected_ai_provider
            )
            is_graph_error = structured_data_dict_docx and structured_data_dict_docx.get("error") or \
                             not pdf_bytes_for_docx or \
                             (b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx)

            if not is_graph_error:
                st.session_state.tab3_cached_graph_output = (pdf_bytes_for_docx, structured_data_dict_docx)
                st.session_state.tab3_cache_key = current_graph_cache_key
                st.caption("Quotation data generated and cached.")
            else:
                st.session_state.tab3_cached_graph_output = None
                st.session_state.tab3_cache_key = None
                st.error(f"Error from quotation graph (for DOCX): {structured_data_dict_docx.get('error', 'Unknown graph error')}")
                if structured_data_dict_docx and structured_data_dict_docx.get('raw_output'):
                    st.expander("Raw LLM Output (DOCX)").text(structured_data_dict_docx['raw_output'])
                if pdf_bytes_for_docx: st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_for_docx # Store error PDF
                return # Stop processing

    # Step 2: Process for DOCX if graph output is available and seems okay
    if pdf_bytes_for_docx and structured_data_dict_docx and not structured_data_dict_docx.get("error"):
        is_error_pdf_content = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
        
        actual_docx_bytes = None
        if not is_error_pdf_content and len(pdf_bytes_for_docx) > 1000 : # Only convert if PDF is valid
            with st.spinner("Converting PDF to DOCX..."):
                actual_docx_bytes = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
        
        _handle_docx_processing_and_storage(
            active_enquiry_id_tab3, actual_docx_bytes, structured_data_dict_docx,
            is_error_pdf_content, pdf_bytes_for_docx
        )
    elif structured_data_dict_docx and structured_data_dict_docx.get("error"): # Error from graph structuring
        st.error(f"Failed to structure data (for DOCX): {structured_data_dict_docx.get('error')}")
        if structured_data_dict_docx.get('raw_output'):
            st.expander("Raw LLM Output (DOCX)").text(structured_data_dict_docx['raw_output'])
        if pdf_bytes_for_docx: # Store error PDF for download
            st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_for_docx