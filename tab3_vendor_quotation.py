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
# No need to import QUOTATIONS_BUCKET_NAME from app, it's passed as a parameter

def render_tab3(QUOTATIONS_BUCKET_NAME_param: str):
    # Use the passed parameter
    QUOTATIONS_BUCKET_NAME = QUOTATIONS_BUCKET_NAME_param

    st.header("3. Add Vendor Reply & Generate Quotation")

    # Display one-time messages if set
    if st.session_state.get('vendor_reply_saved_success_message'):
        st.success(st.session_state.vendor_reply_saved_success_message)
        st.session_state.vendor_reply_saved_success_message = None # Clear after displaying

    enquiries_list_tab3, error_msg_enq_list_tab3 = get_enquiries()
    if error_msg_enq_list_tab3:
        st.error(f"Could not load enquiries for this tab: {error_msg_enq_list_tab3}")
        enquiries_list_tab3 = []

    if not enquiries_list_tab3:
        st.info("No enquiries available. Please submit one in the 'New Enquiry' tab.")
        st.session_state.selected_enquiry_id_tab3 = None
    else:
        enquiry_options_tab3 = {f"{e['id'][:8]}... - {e['destination']}": e['id'] for e in enquiries_list_tab3}

        if st.session_state.selected_enquiry_id_tab3 not in enquiry_options_tab3.values():
            st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0] if enquiry_options_tab3 else None
            # If selection changed, reset tab3 specific states
            if st.session_state.selected_enquiry_id_tab3:
                st.session_state.tab3_enquiry_details = None
                st.session_state.tab3_client_name = "Valued Client"
                st.session_state.tab3_itinerary_info = None
                st.session_state.tab3_vendor_reply_info = None
                st.session_state.tab3_quotation_pdf_bytes = None
                st.session_state.tab3_quotation_docx_bytes = None
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
                st.session_state.show_quotation_success_tab3 = False

        current_selection_index_tab3 = 0
        if st.session_state.selected_enquiry_id_tab3 and enquiry_options_tab3:
            try:
                current_selection_index_tab3 = list(enquiry_options_tab3.values()).index(st.session_state.selected_enquiry_id_tab3)
            except ValueError:
                st.session_state.selected_enquiry_id_tab3 = list(enquiry_options_tab3.values())[0]
                current_selection_index_tab3 = 0
                # Reset states because selection was forced
                st.session_state.tab3_enquiry_details = None
                st.session_state.tab3_client_name = "Valued Client"
                st.session_state.tab3_itinerary_info = None
                st.session_state.tab3_vendor_reply_info = None
                st.session_state.tab3_quotation_pdf_bytes = None
                st.session_state.tab3_quotation_docx_bytes = None
                st.session_state.tab3_current_quotation_db_id = None
                st.session_state.tab3_current_pdf_storage_path = None
                st.session_state.tab3_current_docx_storage_path = None
                st.session_state.show_quotation_success_tab3 = False

        prev_selected_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3
        selected_enquiry_label_tab3 = st.selectbox(
            "Select Enquiry for Vendor Reply & Quotation:",
            options=list(enquiry_options_tab3.keys()),
            index=current_selection_index_tab3,
            key="enquiry_selector_tab3"
        )

        if selected_enquiry_label_tab3:
            st.session_state.selected_enquiry_id_tab3 = enquiry_options_tab3[selected_enquiry_label_tab3]

        if st.session_state.selected_enquiry_id_tab3 != prev_selected_enquiry_id_tab3:
            st.session_state.tab3_enquiry_details = None
            st.session_state.tab3_client_name = "Valued Client"
            st.session_state.tab3_itinerary_info = None
            st.session_state.tab3_vendor_reply_info = None
            st.session_state.tab3_quotation_pdf_bytes = None
            st.session_state.tab3_quotation_docx_bytes = None
            st.session_state.tab3_current_quotation_db_id = None
            st.session_state.tab3_current_pdf_storage_path = None
            st.session_state.tab3_current_docx_storage_path = None
            st.session_state.show_quotation_success_tab3 = False
            st.rerun()

        if st.session_state.selected_enquiry_id_tab3:
            active_enquiry_id_tab3 = st.session_state.selected_enquiry_id_tab3

            # Load enquiry details if not already loaded or if active ID changed
            if st.session_state.tab3_enquiry_details is None or \
               st.session_state.tab3_enquiry_details.get('id') != active_enquiry_id_tab3:
                details, _ = get_enquiry_by_id(active_enquiry_id_tab3)
                st.session_state.tab3_enquiry_details = details

                client_data_for_tab3, _ = get_client_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_client_name = client_data_for_tab3["name"] if client_data_for_tab3 and client_data_for_tab3.get("name") else "Valued Client"

                vendor_reply_data, _ = get_vendor_reply_by_enquiry_id(active_enquiry_id_tab3)
                st.session_state.tab3_vendor_reply_info = {
                    'text': vendor_reply_data['reply_text'] if vendor_reply_data else None,
                    'id': vendor_reply_data['id'] if vendor_reply_data else None
                }
                latest_quotation_record, _ = get_quotation_by_enquiry_id(active_enquiry_id_tab3)
                if latest_quotation_record:
                    st.session_state.tab3_current_quotation_db_id = latest_quotation_record.get('id')
                    st.session_state.tab3_current_pdf_storage_path = latest_quotation_record.get('pdf_storage_path')
                    st.session_state.tab3_current_docx_storage_path = latest_quotation_record.get('docx_storage_path')
                else:
                    st.session_state.tab3_current_quotation_db_id = None
                    st.session_state.tab3_current_pdf_storage_path = None
                    st.session_state.tab3_current_docx_storage_path = None

            # ALWAYS Fetch/Refresh Itinerary for Tab 3 (as it might be updated by Tab 2)
            itinerary_data_tab3, _ = get_itinerary_by_enquiry_id(active_enquiry_id_tab3)
            if itinerary_data_tab3:
                st.session_state.tab3_itinerary_info = {
                    'text': itinerary_data_tab3['itinerary_text'],
                    'id': itinerary_data_tab3['id']
                }
            else: # If no itinerary, set a placeholder structure
                st.session_state.tab3_itinerary_info = {
                    'text': "No AI-generated itinerary/suggestions available for this enquiry. Please generate in Tab 2.",
                    'id': None
                }

            # The 'text' and 'id' for tab3_vendor_reply_info is set above, and updated after form submission below.

            if st.session_state.tab3_enquiry_details:
                st.subheader(f"Working with Enquiry for {st.session_state.tab3_client_name}: {st.session_state.tab3_enquiry_details['destination']} (ID: {active_enquiry_id_tab3[:8]}...)")
                cols_details_tab3 = st.columns(2)
                with cols_details_tab3[0]:
                    st.markdown(f"""
                        - **Destination:** {st.session_state.tab3_enquiry_details['destination']}
                        - **Days:** {st.session_state.tab3_enquiry_details['num_days']}
                        - **Travelers:** {st.session_state.tab3_enquiry_details['traveler_count']}
                    """)
                with cols_details_tab3[1]:
                     st.markdown(f"""
                        - **Trip Type:** {st.session_state.tab3_enquiry_details['trip_type']}
                        - **Status:** {st.session_state.tab3_enquiry_details.get('status', 'New')}
                    """)

                itinerary_display_text_tab3 = st.session_state.tab3_itinerary_info.get('text', "No itinerary information.")
                if "No AI-generated itinerary/suggestions available" not in itinerary_display_text_tab3:
                    with st.expander("View AI Generated Itinerary/Suggestions (from Tab 2)", expanded=False): # Updated expander title
                        st.markdown(itinerary_display_text_tab3)
                else:
                    st.caption(itinerary_display_text_tab3)

                st.markdown("---")
                st.subheader("✍️ Add/View Vendor Reply")
                current_vendor_reply_text_for_form = st.session_state.tab3_vendor_reply_info.get('text', "") if st.session_state.tab3_vendor_reply_info else ""

                if current_vendor_reply_text_for_form:
                    with st.expander("View Current Vendor Reply", expanded=False):
                        st.text_area("Existing Vendor Reply", value=current_vendor_reply_text_for_form, height=150, disabled=True, key=f"disp_vendor_reply_tab3_{active_enquiry_id_tab3}")
                else:
                    st.caption("No vendor reply submitted yet for this enquiry.")

                with st.form(key=f"vendor_reply_form_tab3_{active_enquiry_id_tab3}"):
                    vendor_reply_text_input = st.text_area("Vendor Reply Text (Pricing, Inclusions, etc.)", value=current_vendor_reply_text_for_form, height=200, key=f"new_vendor_reply_text_tab3_{active_enquiry_id_tab3}")
                    submitted_vendor_reply = st.form_submit_button("Submit/Update Vendor Reply")

                    if submitted_vendor_reply:
                        if not vendor_reply_text_input: st.error("Vendor reply text cannot be empty.")
                        else:
                            with st.spinner("Saving vendor reply..."):
                                reply_data, error_msg_reply_add = add_vendor_reply(active_enquiry_id_tab3, vendor_reply_text_input)
                                if reply_data:
                                    st.session_state.vendor_reply_saved_success_message = f"Vendor reply saved successfully for enquiry ID: {active_enquiry_id_tab3[:8]}..."
                                    st.session_state.tab3_vendor_reply_info = {'text': reply_data['reply_text'], 'id': reply_data['id']}
                                    st.session_state.tab3_quotation_pdf_bytes = None
                                    st.session_state.tab3_quotation_docx_bytes = None
                                    st.session_state.show_quotation_success_tab3 = False
                                    st.rerun()
                                else: st.error(f"Failed to save vendor reply. {error_msg_reply_add or 'Unknown error'}")

                st.markdown("---")
                st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")
                vendor_reply_available = st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info.get('text')
                # Get the itinerary text from Tab 2 (or placeholder if not available)
                itinerary_text_for_graph = st.session_state.tab3_itinerary_info.get('text', "Itinerary suggestions not available.")

                if not vendor_reply_available: st.warning("A vendor reply is required to generate quotations.")
                generate_quotation_disabled = not (vendor_reply_available and st.session_state.tab3_enquiry_details)

                col1_gen, col2_gen = st.columns(2)
                # --- PDF GENERATION ---
                with col1_gen:
                    if st.button(f"Generate Quotation PDF", disabled=generate_quotation_disabled, key="generate_pdf_btn_tab3"):
                        st.session_state.tab3_quotation_pdf_bytes = None
                        st.session_state.tab3_current_pdf_storage_path = None # Clear old path for new generation
                        st.session_state.show_quotation_success_tab3 = False

                        with st.spinner(f"Generating PDF data with {st.session_state.selected_ai_provider}..."):
                            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
                            # Removed: current_enquiry_details_for_gen["itinerary_text_from_ui"]

                            pdf_bytes_output, structured_data_dict = run_quotation_generation_graph(
                                enquiry_details=current_enquiry_details_for_gen,
                                vendor_reply_text=st.session_state.tab3_vendor_reply_info['text'],
                                ai_suggested_itinerary_text=itinerary_text_for_graph, # Pass Tab 2 itinerary
                                provider=st.session_state.selected_ai_provider
                            )

                        if structured_data_dict and not structured_data_dict.get("error"):
                            is_error_pdf_content = b"Error generating PDF" in pdf_bytes_output or b"Quotation Generation Failed" in pdf_bytes_output
                            if pdf_bytes_output and not is_error_pdf_content and len(pdf_bytes_output) > 1000: # Basic check for valid PDF
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output
                                pdf_path_for_db = None
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
                                        docx_storage_path=st.session_state.tab3_current_docx_storage_path # Preserve if DOCX was already generated
                                    )
                                    if q_error: st.error(f"Failed to save PDF quotation data: {q_error}")
                                    else:
                                        st.session_state.tab3_current_quotation_db_id = q_data['id']
                                        st.session_state.vendor_reply_saved_success_message = "Quotation PDF generated, uploaded, and data saved!"
                                        st.session_state.show_quotation_success_tab3 = True
                                        st.rerun()
                            else:
                                st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Store even if it's an error PDF
                                st.error("Failed to generate a valid PDF. Error PDF might be available for download.")
                        else:
                            err = structured_data_dict.get('error',"Unknown error from LLM graph") if structured_data_dict else "Graph execution error"
                            st.error(f"Failed to structure data for PDF: {err}")
                            if structured_data_dict and structured_data_dict.get('raw_output'): st.expander("Raw LLM Output").text(structured_data_dict['raw_output'])
                            if pdf_bytes_output: st.session_state.tab3_quotation_pdf_bytes = pdf_bytes_output # Store error PDF


                # --- DOCX GENERATION ---
                with col2_gen:
                    if st.button(f"Generate Quotation DOCX", disabled=generate_quotation_disabled, key="generate_docx_btn_tab3"):
                        st.session_state.tab3_quotation_docx_bytes = None
                        st.session_state.tab3_current_docx_storage_path = None # Clear old path

                        with st.spinner(f"Generating DOCX data with {st.session_state.selected_ai_provider}..."):
                            current_enquiry_details_for_gen = st.session_state.tab3_enquiry_details.copy()
                            current_enquiry_details_for_gen["client_name_actual"] = st.session_state.tab3_client_name
                            # Removed: current_enquiry_details_for_gen["itinerary_text_from_ui"]

                            pdf_bytes_for_docx, structured_data_dict_docx = run_quotation_generation_graph(
                                enquiry_details=current_enquiry_details_for_gen,
                                vendor_reply_text=st.session_state.tab3_vendor_reply_info['text'],
                                ai_suggested_itinerary_text=itinerary_text_for_graph, # Pass Tab 2 itinerary
                                provider=st.session_state.selected_ai_provider
                            )

                        if structured_data_dict_docx and not structured_data_dict_docx.get("error"):
                            is_error_pdf_content_docx = b"Error generating PDF" in pdf_bytes_for_docx or b"Quotation Generation Failed" in pdf_bytes_for_docx
                            if pdf_bytes_for_docx and not is_error_pdf_content_docx and len(pdf_bytes_for_docx) > 1000: # Valid PDF generated
                                with st.spinner("Converting PDF to DOCX..."):
                                    docx_bytes_output = convert_pdf_bytes_to_docx_bytes(pdf_bytes_for_docx)

                                if docx_bytes_output:
                                    st.session_state.tab3_quotation_docx_bytes = docx_bytes_output
                                    docx_path_for_db = None
                                    with st.spinner("Uploading DOCX to cloud storage..."):
                                        ts_docx = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        fn_docx = f"{active_enquiry_id_tab3}/quotation_DOCX_{ts_docx}_{uuid.uuid4().hex[:6]}.docx"
                                        docx_path_for_db, up_err_docx = upload_file_to_storage(QUOTATIONS_BUCKET_NAME, fn_docx, docx_bytes_output, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

                                    if up_err_docx: st.error(f"DOCX generated, but failed to upload: {up_err_docx}")
                                    else: st.session_state.tab3_current_docx_storage_path = docx_path_for_db

                                    with st.spinner("Saving/updating DOCX quotation data..."):
                                        if st.session_state.tab3_current_quotation_db_id: # If a PDF was generated and has a DB ID
                                            _, upd_err = update_quotation_storage_path(st.session_state.tab3_current_quotation_db_id, 'docx_storage_path', docx_path_for_db)
                                            if upd_err: st.error(f"Failed to update DOCX path in DB: {upd_err}")
                                            else:
                                                st.session_state.vendor_reply_saved_success_message = "DOCX generated, uploaded, and DB record updated!"
                                                st.rerun()
                                        else: # Create new record if no PDF was made first or its DB save failed
                                            q_data_dx, q_err_dx = add_quotation(
                                                active_enquiry_id_tab3, structured_data_dict_docx,
                                                st.session_state.tab3_itinerary_info.get('id'),
                                                st.session_state.tab3_vendor_reply_info.get('id'),
                                                pdf_storage_path=st.session_state.tab3_current_pdf_storage_path, # Preserve if PDF was made
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
                            mime="application/pdf", key="local_dl_pdf_tab3" # Unique key
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
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="local_dl_docx_tab3" # Unique key
                        )

                if not has_any_file_info and not st.session_state.get('tab3_quotation_pdf_bytes') and not st.session_state.get('tab3_quotation_docx_bytes'):
                    st.info("No quotation files available. Use 'Generate' buttons to create them.")

            else:
                 st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")
        else:
            st.info("Select an enquiry to manage its vendor reply and quotation.")