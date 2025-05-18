import streamlit as st
from supabase_utils import (
    get_enquiries, get_enquiry_by_id, get_client_by_enquiry_id,
    add_vendor_reply, get_vendor_reply_by_enquiry_id,
    get_itinerary_by_enquiry_id, # Needed to fetch latest itinerary for quotation
    add_quotation, update_quotation_storage_path, get_quotation_by_enquiry_id,
    upload_file_to_storage, get_public_url, create_signed_url
)
from quotation_graph_builder import run_quotation_generation_graph
from docx_utils import convert_pdf_bytes_to_docx_bytes
import uuid # For unique filenames
from datetime import datetime # For timestamp in filenames
import hashlib # For generating cache key

# Helper function to generate a cache key
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
    # Do not reset stored paths (tab3_current_pdf_storage_path, tab3_current_docx_storage_path) here
    # as they represent what's in the DB for the *latest* quotation record.
    # They are reset specifically when a new generation starts for that file type.

def render_tab3(QUOTATIONS_BUCKET_NAME_param: str):
    QUOTATIONS_BUCKET_NAME = QUOTATIONS_BUCKET_NAME_param

    st.header("3. Add Vendor Reply & Generate Quotation")

    if st.session_state.get('vendor_reply_saved_success_message'):
        st.success(st.session_state.vendor_reply_saved_success_message)
        st.session_state.vendor_reply_saved_success_message = None

    enquiries_list_tab3, error_msg_enq_list_tab3 = get_enquiries()
    if error_msg_enq_list_tab3:
        st.error(f"Could not load enquiries: {error_msg_enq_list_tab3}")
        enquiries_list_tab3 = []

    if not enquiries_list_tab3:
        st.info("No enquiries available. Submit one in 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id_tab3 = None
        _reset_tab3_cache_and_outputs() # Reset cache if no enquiries
    else:
        enquiry_options_tab3 = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_list_tab3}

        if st.session_state.selected_enquiry_id_tab3 not in enquiry_options_tab3.values():
            st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0] if enquiry_options_tab3 else None
            if st.session_state.selected_enquiry_id_tab3:
                st.session_state.tab3_enquiry_details = None # Force reload
                _reset_tab3_cache_and_outputs()
                st.session_state.tab3_current_quotation_db_id = None # Reset related quotation info
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None


        current_selection_index_tab3 = 0
        if st.session_state.selected_enquiry_id_tab3 and enquiry_options_tab3:
            try:
                current_selection_index_tab3 = list(enquiry_options_tab3.values()).index(st.session_state.selected_enquiry_id_tab3)
            except ValueError:
                st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0]
                current_selection_index_tab3 = 0
                st.session_state.tab3_enquiry_details = None # Force reload
                _reset_tab3_cache_and_outputs()
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None

        prev_selected_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3
        selected_enquiry_label_tab3 = st.selectbox(
            "Select Enquiry:",
            options=list(enquiry_options_tab3.keys()),
            index=current_selection_index_tab3,
            key="enquiry_selector_tab3"
        )

        if selected_enquiry_label_tab3:
            st.session_state.selected_enquiry_id_tab3 = enquiry_options_tab3[selected_enquiry_label_tab3]

        if st.session_state.selected_enquiry_id_tab3 != prev_selected_enquiry_id_tab3:
            st.session_state.tab3_enquiry_details = None
            _reset_tab3_cache_and_outputs()
            st.session_state.tab3_current_quotation_db_id = None # Also reset related quotation info
            st.session_state.tab3_current_pdf_storage_path = None
            st.session_state.tab3_current_docx_storage_path = None
            st.session_state.show_quotation_success_tab3 = False # Reset success message display
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            if st.session_state.tab3_enquiry_details is None or \
               st.session_state.tab3_enquiry_details.get('id') != active_enquiry_id_tab3:
                details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
                st.session_state.tab3_enquiry_details = details
                client_data, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_client_name = client_data["name"] if client_data else "Valued Client"
                
                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_vendor_reply_info = {'text': vendor_reply_data['reply_text'] if vendor_reply_data else None, 'id': vendor_reply_data['id'] if vendor_reply_data else None}
                
                latest_quotation_rec, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
                if latest_quotation_rec:
                    st.session_state.tab3_current_quotation_db_id = latest_quotation_rec.get('id')
                    st.session_state.tab3_current_pdf_storage_path = latest_quotation_rec.get('pdf_storage_path')
                    st.session_state.tab3_current_docx_storage_path = latest_quotation_rec.get('docx_storage_path')
                else:
                    st.session_state.tab3_current_quotation_db_id = None
                    st.session_state.tab3_current_pdf_storage_path = None
                    st.session_state.tab3_current_docx_storage_path = None
                _reset_tab3_cache_and_outputs() # Reset cache when enquiry details are freshly loaded

            itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
            current_itinerary_text = itinerary_data_tab3['itinerary_text'] if itinerary_data_tab3 else "No AI-generated itinerary/suggestions available. Please generate in Tab 2."
            # Check if itinerary text has changed since last load for this enquiry to invalidate cache
            if st.session_state.tab3_itinerary_info and st.session_state.tab3_itinerary_info.get('text') != current_itinerary_text:
                _reset_tab3_cache_and_outputs()

            st.session_state.tab3_itinerary_info = {'text': current_itinerary_text, 'id': itinerary_data_tab3['id'] if itinerary_data_tab3 else None}


            if st.session_state.tab3_enquiry_details:
                st.subheader(f"Working with Enquiry for {st.session_state.tab3_client_name}: {st.session_state.tab3_enquiry_details['destination']} (ID: {active_enquiry_id_tab3[:8]}...)")
                # Display enquiry details and itinerary expander (code omitted for brevity, same as before)
                itinerary_display_text_tab3 = st.session_state.tab3_itinerary_info.get('text', "No itinerary information.")
                if "No AI-generated itinerary/suggestions available" not in itinerary_display_text_tab3:
                    with st.expander("View AI Generated Itinerary/Suggestions (from Tab 2)", expanded=False):
                        st.markdown(itinerary_display_text_tab3)
                else:
                    st.caption(itinerary_display_text_tab3)

                st.markdown("---")
                st.subheader("✍️ Add/View Vendor Reply")
                current_vendor_reply_text_for_form = st.session_state.tab3_vendor_reply_info.get('text', "") if st.session_state.tab3_vendor_reply_info else ""
                
                # Vendor reply form (code omitted for brevity, with one change)
                with st.form(key=f"vendor_reply_form_tab3_{active_enquiry_id_tab3}"):
                    vendor_reply_text_input = st.text_area("Vendor Reply Text (Pricing, Inclusions, etc.)", value=current_vendor_reply_text_for_form, height=200, key=f"new_vendor_reply_text_tab3_{active_enquiry_id_tab3}")
                    submitted_vendor_reply = st.form_submit_button("Submit/Update Vendor Reply")

                    if submitted_vendor_reply:
                        if not vendor_reply_text_input: st.error("Vendor reply text cannot be empty.")
                        else:
                            with st.spinner("Saving vendor reply..."):
                                reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
                                if reply_data:
                                    st.session_state.vendor_reply_saved_success_message = f"Vendor reply saved for enquiry ID: {active_enquiry_id_tab3[:8]}..."
                                    st.session_state.tab3_vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
                                    _reset_tab3_cache_and_outputs() # Crucial: Reset cache on vendor reply update
                                    st.session_state.show_quotation_success_tab3 = False
                                    st.rerun()
                                else: st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")
                
                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")
                vendor_reply_available = st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info.get('text')
                itinerary_text_for_graph = st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available.")
                
                if not vendor_reply_available: st.warning("A vendor reply is required to generate quotations.")
                generate_quotation_disabled = not (vendor_reply_available and st.session_state.tab3_enquiry_details)

                current_graph_cache_key = _generate_graph_cache_key(
                    active_enquiry_id_tab3,
                    st.session_state.tab3_client_name,
                    st.session_state.tab3_vendor_reply_info.get('text', ""),
                    itinerary_text_for_graph,
                    st.session_state.selected_ai_provider,
                    st.session_state.get('selected_model_for_provider')
                )

                col1_gen, col2_gen = st.columns(2)
                with col1_gen:
                    if st.button(f"Generate Quotation PDF", disabled=generate_quotation_disabled, key="generate_pdf_btn_tab3"):
                        st.session_state.tab3_quotation_pdf_bytes = None # Clear local download bytes
                        st.session_state.tab3_current_pdf_storage_path = None # Clear stored path for new generation
                        st.session_state.show_quotation_success_tab3 = False
                        
                        pdf_bytes_output, structured_data_dict = None, None

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
                                else:
                                    _reset_tab3_cache_and_outputs() # Clear cache on error

                        if structured_data_dict and not structured_data_dict.get("error"):
                            is_error_pdf_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
                            if pdf_bytes_output and not is_error_pdf_content and len(pdf_bytes_output) > 1000:
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                                pdf_path_for_db = None
                                # ... (rest of PDF upload and DB save logic, same as before) ...
                                with st.spinner("Uploading PDF to cloud storage..."):
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    fn = f"{active_enquiry_id_tab3}/quotation_PDF_{timestamp}_{uuid.uuid4().hex[:6]}.pdf"
                                    pdf_path_for_db, upload_err = upload_file_to_storage(QUOTATIONS_BUCKET_NAME, fn, pdf_bytes_output, "application/pdf")
                                
                                if upload_err: st.error(f"PDF generated, but failed to upload: {upload_err}")
                                else: st.session_state.tab3_current_pdf_storage_path = pdf_path_for_db 

                                with st.spinner("Saving quotation data to database..."):
                                    q_data, q_error = add_quotation(
                                        active_enquiry_id_tab3, structured_data_dict, 
                                        st.session_state.tab3_itinerary_info.get('id'), 
                                        st.session_state.tab3_vendor_reply_info.get('id'),
                                        pdf_storage_path=pdf_path_for_db,
                                        docx_storage_path=st.session_state.tab3_current_docx_storage_path
                                    )
                                    if q_error: st.error(f"Failed to save PDF quotation data: {q_error}")
                                    else:
                                        st.session_state.tab3_current_quotation_db_id = q_data['id']
                                        st.session_state.vendor_reply_saved_success_message = "Quotation PDF generated, uploaded, and data saved!"
                                        st.session_state.show_quotation_success_tab3 = True
                                        st.rerun()
                            else: 
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output 
                                st.error("Failed to generate a valid PDF. Error PDF might be available for download.")
                        else:
                            err = structured_data_dict.get('error',"Unknown error from LLM graph") if structured_data_dict else "Graph execution error"
                            st.error(f"Failed to structure data for PDF: {err}")
                            if structured_data_dict and structured_data_dict.get('raw_output'): st.expander("Raw LLM Output").text(structured_data_dict['raw_output'])
                            if pdf_bytes_output: st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                
                with col2_gen:
                    if st.button(f"Generate Quotation DOCX", disabled=generate_quotation_disabled, key="generate_docx_btn_tab3"):
                        st.session_state.tab3_quotation_docx_bytes = None
                        st.session_state.tab3_current_docx_storage_path = None
                        
                        pdf_bytes_for_docx, structured_data_dict_docx = None, None

                        if st.session_state.tab3_cached_graph_output and st.session_state.tab3_cache_key == current_graph_cache_key:
                            st.info("Using cached data for DOCX generation.")
                            pdf_bytes_for_docx, structured_data_dict_docx = st.session_state.tab3_cached_graph_output
                        else:
                            with st.spinner(f"Generating DOCX data with {st.session_state.selected_ai_provider}..."):
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
                                else:
                                    _reset_tab3_cache_and_outputs()

                        if structured_data_dict_docx and not structured_data_dict_docx.get("error"):
                            is_error_pdf_content_docx = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
                            if pdf_bytes_for_docx and not is_error_pdf_content_docx and len(pdf_bytes_for_docx) > 1000:
                                with st.spinner("Converting PDF to DOCX..."):
                                    docx_bytes_output = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)
                                
                                if docx_bytes_output:
                                    st.session_state.tab3_quotation_docx_bytes = docx_bytes_output
                                    docx_path_for_db = None
                                    # ... (rest of DOCX upload and DB save/update logic, same as before) ...
                                    with st.spinner("Uploading DOCX to cloud storage..."):
                                        ts_docx = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        fn_docx = f"{active_enquiry_id_tab3}/quotation_DOCX_{ts_docx}_{uuid.uuid4().hex[:6]}.docx"
                                        docx_path_for_db, up_err_docx = upload_file_to_storage(QUOTATIONS_BUCKET_NAME, fn_docx, docx_bytes_output, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                                    
                                    if up_err_docx: st.error(f"DOCX generated, but failed to upload: {up_err_docx}")
                                    else: st.session_state.tab3_current_docx_storage_path = docx_path_for_db

                                    with st.spinner("Saving/updating DOCX quotation data..."):
                                        if st.session_state.tab3_current_quotation_db_id: 
                                            _, upd_err = update_quotation_storage_path(st.session_state.tab3_current_quotation_db_id, 'docx_storage_path', docx_path_for_db)
                                            if upd_err: st.error(f"Failed to update DOCX path in DB: {upd_err}")
                                            else: 
                                                st.session_state.vendor_reply_saved_success_message = "DOCX generated, uploaded, and DB record updated!"
                                                st.rerun()
                                        else: 
                                            q_data_dx, q_err_dx = add_quotation(
                                                active_enquiry_id_tab3, structured_data_dict_docx, 
                                                st.session_state.tab3_itinerary_info.get('id'), 
                                                st.session_state.tab3_vendor_reply_info.get('id'),
                                                pdf_storage_path=st.session_state.tab3_current_pdf_storage_path, 
                                                docx_storage_path=docx_path_for_db
                                            )
                                            if q_err_dx: st.error(f"Failed to save DOCX quotation data: {q_err_dx}")
                                            else:
                                                st.session_state.tab3_current_quotation_db_id = q_data_dx['id']
                                                st.session_state.vendor_reply_saved_success_message = "DOCX generated, uploaded, and new data record saved!"
                                                st.rerun()
                                else: st.error("Failed to convert PDF to DOCX.")
                            else: 
                                st.error("Could not generate underlying PDF for DOCX conversion.")
                                if pdf_bytes_for_docx: 
                                    st.download_button("Download Intermediate Error PDF", pdf_bytes_for_docx, "Error_PDF_for_DOCX.pdf", "application/pdf", key="err_pdf_docx")
                        else:
                            err_dx = structured_data_dict_docx.get('error',"Unknown error from LLM graph") if structured_data_dict_docx else "Graph execution error"
                            st.error(f"Failed to structure data for DOCX: {err_dx}")
                            if structured_data_dict_docx and structured_data_dict_docx.get('raw_output'): st.expander("Raw LLM Output (DOCX)").text(structured_data_dict_docx['raw_output'])
                
                st.markdown("---")
                st.subheader("Download/View Quotation Files")
                # Download/View section (code omitted for brevity, same as before)
                has_any_file_info = False
                dl_col1_show, dl_col2_show = st.columns(2)

                with dl_col1_show:
                    st.markdown("**PDF Document**")
                    pdf_path_to_show = st.session_state.get('tab3_current_pdf_storage_path')
                    if pdf_path_to_show:
                        has_any_file_info = True
                        pdf_public_url = get_public_url(QUOTATIONS_BUCKET_NAME, pdf_path_to_show)
                        if pdf_public_url: st.markdown(f"[:cloud: View/Download Stored PDF]({pdf_public_url})", unsafe_allow_html=True)
                        else:
                            signed_url_pdf, err_sign_pdf = create_signed_url(QUOTATIONS_BUCKET_NAME, pdf_path_to_show)
                            if signed_url_pdf: st.markdown(f"[:lock: Download Stored PDF (Signed URL)]({signed_url_pdf})", unsafe_allow_html=True)
                            elif err_sign_pdf: st.caption(f"URL Error: {err_sign_pdf}")
                    else:
                        st.caption("No PDF stored for latest quotation.")

                    if st.session_state.get('tab3_quotation_pdf_bytes'):
                        has_any_file_info = True
                        st.download_button(
                            label="Download Locally Generated PDF", data=st.session_state.tab3_quotation_pdf_bytes,
                            file_name=f"Local_PDF_{st.session_state.tab3_enquiry_details.get('destination','Q')}_{active_enquiry_id_tab3[:4]}.pdf",
                            mime="application/pdf", key="local_dl_pdf_tab3"
                        )

                with dl_col2_show:
                    st.markdown("**DOCX Document**")
                    docx_path_to_show = st.session_state.get('tab3_current_docx_storage_path')
                    if docx_path_to_show:
                        has_any_file_info = True
                        docx_public_url = get_public_url(QUOTATIONS_BUCKET_NAME, docx_path_to_show)
                        if docx_public_url: st.markdown(f"[:cloud: View/Download Stored DOCX]({docx_public_url})", unsafe_allow_html=True)
                        else:
                            signed_url_docx, err_sign_docx = create_signed_url(QUOTATIONS_BUCKET_NAME, docx_path_to_show)
                            if signed_url_docx: st.markdown(f"[:lock: Download Stored DOCX (Signed URL)]({signed_url_docx})", unsafe_allow_html=True)
                            elif err_sign_docx: st.caption(f"URL Error: {err_sign_docx}")
                    else:
                        st.caption("No DOCX stored for latest quotation.")
                    
                    if st.session_state.get('tab3_quotation_docx_bytes'):
                        has_any_file_info = True
                        st.download_button(
                            label="Download Locally Generated DOCX", data=st.session_state.tab3_quotation_docx_bytes,
                            file_name=f"Local_DOCX_{st.session_state.tab3_enquiry_details.get('destination','Q')}_{active_enquiry_id_tab3[:4]}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="local_dl_docx_tab3"
                        )
                
                if not has_any_file_info and not st.session_state.get('tab3_quotation_pdf_bytes') and not st.session_state.get('tab3_quotation_docx_bytes'):
                    st.info("No quotation files available. Use 'Generate' buttons to create them.")


            else: 
                 st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")
        else:
            st.info("Select an enquiry to manage its vendor reply and quotation.")