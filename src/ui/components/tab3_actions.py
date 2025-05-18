# src/ui/components/tab3_actions.py
import streamlit as st
from src.utils.supabase_utils import (
    add_vendor_reply,
    add_quotation, update_quotation_storage_path,
    upload_file_to_storage
)
from src.core.quotation_graph_builder import run_quotation_generation_graph
from src.utils.docx_utils import convert_pdf_bytes_to_docx_bytes
from src.utils.constants import BUCKET_QUOTATIONS # Import constant
import uuid
from datetime import datetime

def handle_vendor_reply_submit(active_enquiry_id_tab3: str, vendor_reply_text_input: str):
    if not vendor_reply_text_input:
        st.error("Vendor reply text cannot be empty.")
        return

    with st.spinner("Saving vendor reply..."):
        reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
        if reply_data:
            st.session_state.app_state.operation_success_message = f"Vendor reply saved for enquiry ID: {active_enquiry_id_tab3[:8]}..."
            st.session_state.app_state.tab3_state.vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
            # Invalidate graph cache and clear outputs as vendor reply changed
            st.session_state.app_state.tab3_state.cached_graph_output = None
            st.session_state.app_state.tab3_state.cache_key = None
            st.session_state.app_state.tab3_state.quotation_pdf_bytes = None
            st.session_state.app_state.tab3_state.quotation_docx_bytes = None
            st.session_state.app_state.tab3_state.show_quotation_success = False
            # Reset current quotation DB record info as it's tied to the previous vendor reply
            st.session_state.app_state.tab3_state.current_quotation_db_id = None
            st.session_state.app_state.tab3_state.current_pdf_storage_path = None
            st.session_state.app_state.tab3_state.current_docx_storage_path = None
            st.rerun()
        else:
            st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")

# --- Refactored Helper Functions for PDF/DOCX processing ---
def _handle_pdf_processing_and_storage(
    active_enquiry_id: str,
    pdf_bytes_output: bytes,
    structured_data_dict: dict,
    is_error_content_in_pdf: bool # True if pdf_bytes_output represents an error document from the graph
):
    """Handles PDF specific processing: storage, DB update, session state."""
    # Store the generated PDF bytes in session state for local download, regardless of success/error content
    st.session_state.app_state.tab3_state.quotation_pdf_bytes = pdf_bytes_output
    
    if pdf_bytes_output and not is_error_content_in_pdf and len(pdf_bytes_output) > 1000: # Basic validity check for actual content
        storage_path_for_db = None
        with st.spinner("Uploading PDF to cloud storage..."):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"{active_enquiry_id}/quotation_PDF_{timestamp}_{uuid.uuid4().hex[:6]}.pdf"
            storage_path_for_db, upload_err = upload_file_to_storage(
                BUCKET_QUOTATIONS, fn, pdf_bytes_output, "application/pdf"
            )
        
        if upload_err:
            st.error(f"PDF generated, but failed to upload: {upload_err}")
        else:
            st.session_state.app_state.tab3_state.current_pdf_storage_path = storage_path_for_db

        with st.spinner("Saving PDF quotation data to database..."):
            # PDF generation always creates a new quotation record.
            # docx_storage_path is None here because it's reset before PDF gen.
            # If DOCX is generated later, it will update this record.
            q_data, q_error = add_quotation(
                enquiry_id=active_enquiry_id,
                structured_data_json=structured_data_dict,
                itinerary_used_id=st.session_state.app_state.tab3_state.itinerary_info.get('id'),
                vendor_reply_used_id=st.session_state.app_state.tab3_state.vendor_reply_info.get('id'),
                pdf_storage_path=storage_path_for_db,
                docx_storage_path=None 
            )
            if q_error:
                st.error(f"Failed to save PDF quotation data: {q_error}")
            else:
                st.session_state.app_state.tab3_state.current_quotation_db_id = q_data['id']
                if not upload_err: 
                    st.session_state.app_state.operation_success_message = "Quotation PDF generated, uploaded, and data saved!"
                else:
                    st.session_state.app_state.operation_success_message = "Quotation PDF generated and data saved (upload failed)."
                st.session_state.app_state.tab3_state.show_quotation_success = True
                st.rerun() 
    else:
        # This case means pdf_bytes_output was None, too small, or flagged as error content
        st.error("Failed to generate a valid PDF for storage. An error PDF might be available for local download.")
        st.session_state.app_state.tab3_state.show_quotation_success = False # No full success

def _handle_docx_processing_and_storage(
    active_enquiry_id: str,
    docx_bytes_for_upload: bytes | None, # Actual DOCX bytes
    structured_data_dict: dict, # From the graph (same as for PDF)
    is_source_pdf_an_error_document: bool, # Info about the source PDF
    source_pdf_bytes: bytes # The PDF from which DOCX was (or was attempted to be) converted
):
    """Handles DOCX specific processing: storage, DB update, session state."""
    # Store DOCX bytes in session state if successfully generated
    st.session_state.app_state.tab3_state.quotation_docx_bytes = docx_bytes_for_upload
    
    if docx_bytes_for_upload: # DOCX conversion was successful
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
            st.session_state.app_state.tab3_state.current_docx_storage_path = storage_path_for_db_docx
        
        with st.spinner("Saving/updating DOCX quotation data..."):
            existing_quotation_id = st.session_state.app_state.tab3_state.current_quotation_db_id
            
            if existing_quotation_id: # A PDF was likely generated first and record exists
                _, upd_err = update_quotation_storage_path(
                    existing_quotation_id, 'docx_storage_path', storage_path_for_db_docx
                )
                if upd_err:
                    st.error(f"Failed to update DOCX path in DB: {upd_err}")
                else:
                    if not up_err_docx:
                        st.session_state.app_state.operation_success_message = "DOCX generated, uploaded, and DB record updated!"
                    else:
                         st.session_state.app_state.operation_success_message = "DOCX generated and DB record updated (upload failed)!"
                    st.rerun()
            else: # No existing record (e.g., DOCX generated before PDF or PDF failed to save to DB)
                  # Create a new quotation record primarily for this DOCX.
                  # PDF path might be None or from a previous failed attempt stored in session.
                q_data_dx, q_err_dx = add_quotation(
                    active_enquiry_id, structured_data_dict,
                    st.session_state.app_state.tab3_state.itinerary_info.get('id'),
                    st.session_state.app_state.tab3_state.vendor_reply_info.get('id'),
                    pdf_storage_path=st.session_state.app_state.tab3_state.current_pdf_storage_path, 
                    docx_storage_path=storage_path_for_db_docx
                )
                if q_err_dx:
                    st.error(f"Failed to save new DOCX quotation data: {q_err_dx}")
                else:
                    st.session_state.app_state.tab3_state.current_quotation_db_id = q_data_dx['id']
                    if not up_err_docx:
                        st.session_state.app_state.operation_success_message = "DOCX generated, uploaded, and new data record saved!"
                    else:
                        st.session_state.app_state.operation_success_message = "DOCX generated and new data record saved (upload failed)!"
                    st.rerun()
        st.session_state.app_state.tab3_state.show_quotation_success = True

    else: # DOCX conversion failed or original PDF was an error doc
        if is_source_pdf_an_error_document:
            st.error("Could not generate DOCX because the underlying PDF data was an error document or invalid.")
            if source_pdf_bytes: 
                st.download_button(
                    "Download Intermediate PDF (source for DOCX)", source_pdf_bytes, 
                    f"Source_PDF_for_DOCX_{active_enquiry_id[:4]}.pdf", "application/pdf", 
                    key="err_pdf_docx_action_dl"
                )
        else: # actual_docx_bytes is None but source_pdf was not an error document
            st.error("Failed to convert PDF to DOCX.")
        st.session_state.app_state.tab3_state.show_quotation_success = False

# --- Centralized Quotation Graph Data Generation ---
def _get_or_generate_quotation_graph_data(current_graph_cache_key: str) -> tuple[bytes | None, dict | None, bool]:
    """
    Retrieves quotation graph data (PDF bytes, structured JSON) from cache or generates it.
    Returns:
        tuple: (pdf_bytes, structured_data, has_critical_error)
               pdf_bytes and structured_data can be None if critical error.
               has_critical_error is True if generation failed critically.
               If pdf_bytes are returned, they are also stored in st.session_state.app_state.tab3_state.quotation_pdf_bytes.
    """
    if st.session_state.app_state.tab3_state.cached_graph_output and st.session_state.app_state.tab3_state.cache_key == current_graph_cache_key:
        st.info("Using cached data for quotation generation.")
        pdf_bytes, structured_data = st.session_state.app_state.tab3_state.cached_graph_output
        st.session_state.app_state.tab3_state.quotation_pdf_bytes = pdf_bytes 
        return pdf_bytes, structured_data, False 

    itinerary_text_for_graph = st.session_state.app_state.tab3_state.itinerary_info.get('text', "Itinerary suggestions not available.")
    current_enquiry_details_for_gen = st.session_state.app_state.tab3_state.enquiry_details.copy()
    current_enquiry_details_for_gen["client_name_actual"] = st.session_state.app_state.tab3_state.client_name
    provider_for_generation = st.session_state.app_state.ai_config.selected_ai_provider
    
    with st.spinner(f"Generating quotation data with {provider_for_generation}..."):
        pdf_bytes_output, structured_data_dict = run_quotation_generation_graph(
            current_enquiry_details_for_gen,
            st.session_state.app_state.tab3_state.vendor_reply_info['text'],
            itinerary_text_for_graph,
            provider_for_generation
        )
    
    if pdf_bytes_output:
        st.session_state.app_state.tab3_state.quotation_pdf_bytes = pdf_bytes_output

    # Check if the graph itself or the data structuring reported an error
    # structured_data_dict should always be a dict, potentially with an "error" key
    is_data_error = structured_data_dict and structured_data_dict.get("error")
    
    # A "valid" PDF might still be an error PDF if is_data_error is true.
    # Critical error means either no PDF, or data itself has an error flag.
    has_critical_error = not pdf_bytes_output or is_data_error

    if not has_critical_error:
        st.session_state.app_state.tab3_state.cached_graph_output = (pdf_bytes_output, structured_data_dict)
        st.session_state.app_state.tab3_state.cache_key = current_graph_cache_key
        st.caption("Quotation data generated and cached.")
        return pdf_bytes_output, structured_data_dict, False
    else: # Some error occurred
        st.session_state.app_state.tab3_state.cached_graph_output = None
        st.session_state.app_state.tab3_state.cache_key = None
        
        # Prepare error display
        error_message_display = "Quotation data generation failed."
        error_details_display = ""
        error_raw_output_display = ""
        error_type_display = "UnknownError"

        if structured_data_dict: # Error info should be in structured_data_dict
            error_message_display = structured_data_dict.get("error", error_message_display)
            error_details_display = str(structured_data_dict.get("details", ""))
            error_raw_output_display = str(structured_data_dict.get("raw_output", ""))
            error_type_display = str(structured_data_dict.get("type", "UnknownErrorInGraph"))
        elif not pdf_bytes_output:
            error_message_display = "Critical error: PDF generation process returned no output."
            error_type_display = "NoPdfBytes"

        st.error(f"AI Quotation Error ({error_type_display}): {error_message_display}")
        
        if error_details_display or error_raw_output_display:
            with st.expander("Error Details & Technical Information"):
                if error_details_display:
                    st.markdown(f"**Details:**\n```\n{error_details_display}\n```")
                if error_raw_output_display:
                    st.markdown(f"**Raw Output/Context (truncated):**\n```\n{error_raw_output_display[:1000]}\n```")
        
        # pdf_bytes_output here might be an error PDF generated by the graph, or None
        return pdf_bytes_output, structured_data_dict, True

# --- Main PDF/DOCX Generation Triggers ---
def handle_pdf_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str):
    # Reset states for a new PDF generation attempt
    st.session_state.app_state.tab3_state.quotation_pdf_bytes = None
    st.session_state.app_state.tab3_state.current_pdf_storage_path = None
    st.session_state.app_state.tab3_state.quotation_docx_bytes = None 
    st.session_state.app_state.tab3_state.current_docx_storage_path = None
    st.session_state.app_state.tab3_state.current_quotation_db_id = None # PDF generation creates a new quotation record
    st.session_state.app_state.tab3_state.show_quotation_success = False
    
    pdf_bytes_output, structured_data_dict, has_critical_error = \
        _get_or_generate_quotation_graph_data(current_graph_cache_key)

    if has_critical_error:
        st.error("PDF generation halted due to errors in data generation.")
        # Error messages already shown. Error PDF (if any) is in st.session_state.app_state.tab3_state.quotation_pdf_bytes
        return

    # If no critical error, pdf_bytes_output and structured_data_dict are considered "valid" from graph.
    # The `is_error_content_in_pdf` for `_handle_pdf_processing_and_storage` is to distinguish
    # a semantically correct PDF vs. one that the graph *itself* filled with error text.
    # `has_critical_error` already covers explicit error flags from the graph.
    # For `_handle_pdf_processing_and_storage`, if `has_critical_error` is False, we assume the PDF is not an "error PDF".
    _handle_pdf_processing_and_storage(
        active_enquiry_id_tab3, 
        pdf_bytes_output, 
        structured_data_dict, 
        is_error_content_in_pdf=False # Assumed False if has_critical_error was False
    )

def handle_docx_generation(active_enquiry_id_tab3: str, current_graph_cache_key: str):
    # Reset only DOCX specific states; PDF/quotation_db_id might be from a preceding PDF generation
    st.session_state.app_state.tab3_state.quotation_docx_bytes = None
    st.session_state.app_state.tab3_state.current_docx_storage_path = None 
    st.session_state.app_state.tab3_state.show_quotation_success = False
    
    pdf_bytes_for_docx, structured_data_dict_docx, has_critical_error = \
        _get_or_generate_quotation_graph_data(current_graph_cache_key)

    if has_critical_error:
        st.error("DOCX generation halted due to errors in underlying data generation.")
        # Error PDF (if any) is in st.session_state.app_state.tab3_state.quotation_pdf_bytes via the helper
        return

    # If `has_critical_error` is False, `pdf_bytes_for_docx` is assumed not an "error PDF" from graph's view.
    is_source_pdf_an_error_document_for_conversion = False 
    actual_docx_bytes = None
    
    if pdf_bytes_for_docx and len(pdf_bytes_for_docx) > 1000: # Basic check for viable PDF size
        with st.spinner("Converting PDF to DOCX..."):
            actual_docx_bytes = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
    elif pdf_bytes_for_docx: # PDF exists but is too small or potentially problematic
        is_source_pdf_an_error_document_for_conversion = True 
        st.warning("Underlying PDF data is too small or seems invalid for DOCX conversion.")
    else: # No PDF bytes returned from graph data step, should have been caught by has_critical_error
        is_source_pdf_an_error_document_for_conversion = True
        st.error("Cannot generate DOCX: No underlying PDF data available.")


    _handle_docx_processing_and_storage(
        active_enquiry_id_tab3, 
        actual_docx_bytes, 
        structured_data_dict_docx,
        is_source_pdf_an_error_document_for_conversion, 
        pdf_bytes_for_docx # Pass original PDF bytes for download if DOCX fails
    )