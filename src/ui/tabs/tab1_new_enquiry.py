import streamlit as st
from src.utils.supabase_utils import add_enquiry, add_client

def render_tab1():
    st.header("1. Submit New Enquiry")
    with st.form("new_enquiry_form"):
        st.subheader("Travel Details")
        destination = st.text_input("Destination", placeholder="e.g., Paris, France")
        num_days = st.number_input("Number of Days", min_value=1, value=7)
        traveler_count = st.number_input("Number of Travelers", min_value=1, value=2)
        trip_type = st.selectbox("Trip Type", ["Leisure", "Business", "Adventure", "Honeymoon", "Family"])

        st.subheader("Client Information")
        client_name_input = st.text_input("Client Name", placeholder="John Doe")
        client_mobile_input = st.text_input("Mobile Number", placeholder="+91XXXXXXXXXX")
        client_city_input = st.text_input("City", placeholder="Mumbai")
        client_email_input = st.text_input("Email (optional)", placeholder="john@example.com")

        submitted_enquiry = st.form_submit_button("Submit Enquiry")
        if submitted_enquiry:
            if not destination:
                st.error("Destination is required.")
            elif not client_name_input or not client_mobile_input or not client_city_input:
                st.error("Client name, mobile and city are required.")
            else:
                with st.spinner("Submitting enquiry..."):
                    enquiry_data, error_msg = add_enquiry(destination, num_days, traveler_count, trip_type)
                    if enquiry_data:
                        client_data, client_error = add_client(
                            enquiry_id=enquiry_data['id'],
                            name=client_name_input,
                            mobile=client_mobile_input,
                            city=client_city_input,
                            email=client_email_input
                        )

                        if client_data:
                            st.success(f"Enquiry and client information submitted successfully! ID: {enquiry_data['id']}")
                            # Reset relevant session states for a clean slate on other tabs
                            st.session_state.app_state.tab2_state.selected_enquiry_id = enquiry_data['id'] # For Tab 2
                            st.session_state.app_state.tab2_state.current_ai_suggestions = None
                            st.session_state.app_state.tab2_state.current_ai_suggestions_id = None
                            st.session_state.app_state.tab2_state.itinerary_loaded_for_tab2 = None # Reset tab2 specific flag

                            st.session_state.app_state.tab3_state.selected_enquiry_id = enquiry_data['id'] # Auto-select in Tab 3
                            st.session_state.app_state.tab3_state.enquiry_details = None # Force reload in Tab 3
                            st.session_state.app_state.tab3_state.client_name = client_name_input
                            st.session_state.app_state.tab3_state.itinerary_info = None
                            st.session_state.app_state.tab3_state.vendor_reply_info = None
                            st.session_state.app_state.tab3_state.quotation_pdf_bytes = None
                            st.session_state.app_state.tab3_state.quotation_docx_bytes = None
                            st.session_state.app_state.tab3_state.current_quotation_db_id = None
                            st.session_state.app_state.tab3_state.current_pdf_storage_path = None
                            st.session_state.app_state.tab3_state.current_docx_storage_path = None
                            st.session_state.app_state.tab3_state.show_quotation_success = False
                            st.session_state.app_state.operation_success_message = None # This was already correct

                            # Reset Tab 3 quotation graph cache
                            st.session_state.app_state.tab3_state.cached_graph_output = None
                            st.session_state.app_state.tab3_state.cache_key = None
                        else:
                            st.error(f"Enquiry submitted (ID: {enquiry_data['id']}) but failed to save client information. {client_error if client_error else 'Unknown error'}")
                    else:
                        st.error(f"Failed to submit enquiry. {error_msg if error_msg else 'Unknown error'}")