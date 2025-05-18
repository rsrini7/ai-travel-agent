import streamlit as st
from src.utils.supabase_utils import get_public_url, create_signed_url
from src.utils.constants import BUCKET_QUOTATIONS

def display_enquiry_and_itinerary_details_tab3(active_enquiry_id_tab3):
    """Displays selected enquiry details and AI-generated itinerary."""
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
            with st.expander("View AI Generated Itinerary/Suggestions (from Tab 2)", expanded=False):
                st.markdown(itinerary_display_text_tab3)
        else:
            st.caption(itinerary_display_text_tab3)
    else:
        st.error(f"Could not load details for the selected enquiry (ID: {active_enquiry_id_tab3[:8]}...).")


def render_vendor_reply_section(active_enquiry_id_tab3, handle_vendor_reply_submit_func):
    """Renders the vendor reply input/display form and calls the submit handler."""
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
            handle_vendor_reply_submit_func(active_enquiry_id_tab3, vendor_reply_text_input)


def render_quotation_generation_section(active_enquiry_id_tab3, handle_pdf_generation_func, handle_docx_generation_func, current_graph_cache_key):
    """Renders the quotation generation buttons and calls their respective handlers."""
    st.markdown("---")
    st.subheader(f"📄 AI Quotation Generation (using {st.session_state.selected_ai_provider})")
    vendor_reply_available = st.session_state.tab3_vendor_reply_info and st.session_state.tab3_vendor_reply_info.get('text')

    if not vendor_reply_available:
        st.warning("A vendor reply is required to generate quotations.")
    generate_quotation_disabled = not (vendor_reply_available and st.session_state.tab3_enquiry_details)

    col1_gen, col2_gen = st.columns(2)
    with col1_gen:
        if st.button(f"Generate Quotation PDF", disabled=generate_quotation_disabled, key="generate_pdf_btn_tab3"):
            handle_pdf_generation_func(active_enquiry_id_tab3, current_graph_cache_key)
    with col2_gen:
        if st.button(f"Generate Quotation DOCX", disabled=generate_quotation_disabled, key="generate_docx_btn_tab3"):
            handle_docx_generation_func(active_enquiry_id_tab3, current_graph_cache_key)


def display_quotation_files_section(active_enquiry_id_tab3):
    """Displays download/view links for generated quotation files."""
    st.markdown("---")
    st.subheader("Download/View Quotation Files")

    has_any_file_info = False
    dl_col1_show, dl_col2_show = st.columns(2)

    with dl_col1_show:
        st.markdown("**PDF Document**")
        pdf_path_to_show = st.session_state.get('tab3_current_pdf_storage_path')
        if pdf_path_to_show:
            has_any_file_info = True
            pdf_public_url = get_public_url(BUCKET_QUOTATIONS, pdf_path_to_show)
            if pdf_public_url:
                st.markdown(f"[:cloud: View/Download Stored PDF]({pdf_public_url})", unsafe_allow_html=True)
            else:
                signed_url_pdf, err_sign_pdf = create_signed_url(BUCKET_QUOTATIONS, pdf_path_to_show)
                if signed_url_pdf:
                    st.markdown(f"[:lock: Download Stored PDF (Signed URL)]({signed_url_pdf})", unsafe_allow_html=True)
                elif err_sign_pdf:
                    st.caption(f"URL Error: {err_sign_pdf}")
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
            docx_public_url = get_public_url(BUCKET_QUOTATIONS, docx_path_to_show)
            if docx_public_url:
                st.markdown(f"[:cloud: View/Download Stored DOCX]({docx_public_url})", unsafe_allow_html=True)
            else:
                signed_url_docx, err_sign_docx = create_signed_url(BUCKET_QUOTATIONS, docx_path_to_show)
                if signed_url_docx:
                    st.markdown(f"[:lock: Download Stored DOCX (Signed URL)]({signed_url_docx})", unsafe_allow_html=True)
                elif err_sign_docx:
                    st.caption(f"URL Error: {err_sign_docx}")
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