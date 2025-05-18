# ui_helpers.py
import streamlit as st
from supabase_utils import get_enquiries

def handle_enquiry_selection(
    st_object,  # Streamlit object (st or a column/container)
    session_state_key_for_selected_id: str,
    selectbox_label: str,
    on_selection_change_callback: callable,
    no_enquiries_message: str = "No enquiries available. Please submit one first."
):
    """
    Manages the enquiry selection dropdown and related state.

    Args:
        st_object: The Streamlit object to use for displaying UI elements (e.g., st, st.sidebar).
        session_state_key_for_selected_id: The key used in st.session_state to store the selected enquiry ID.
        selectbox_label: The label for the Streamlit selectbox.
        on_selection_change_callback: A function to call when the selected enquiry changes.
                                      This callback is responsible for resetting tab-specific states.
        no_enquiries_message: Message to display if no enquiries are found.

    Returns:
        tuple: (selected_enquiry_id, enquiries_list)
               selected_enquiry_id can be None if no enquiries or no selection.
               enquiries_list is the list of fetched enquiries.
    """
    enquiries_list, error_msg_enq_list = get_enquiries()

    if error_msg_enq_list:
        st_object.error(f"Could not load enquiries: {error_msg_enq_list}")
        enquiries_list = []

    if not enquiries_list:
        st_object.info(no_enquiries_message)
        if st.session_state.get(session_state_key_for_selected_id) is not None:
            st.session_state[session_state_key_for_selected_id] = None
            on_selection_change_callback()  # Trigger reset
        return None, []

    enquiry_options = {
        f"{e['id'][:8]}... - {e['destination']} ({e.get('created_at', 'N/A')[:10]})": e['id']
        for e in enquiries_list
    }

    # Initialize or validate current selection in session state
    current_selected_id_in_state = st.session_state.get(session_state_key_for_selected_id)

    if current_selected_id_in_state not in enquiry_options.values():
        # If current selection is invalid or not set, pick the first one
        current_selected_id_in_state = list(enquiry_options.values())[0] if enquiry_options else None
        st.session_state[session_state_key_for_selected_id] = current_selected_id_in_state
        # If selection was forced (e.g., first load, or invalid previous), trigger callback
        if current_selected_id_in_state is not None:
             on_selection_change_callback() # This ensures data loads for the newly defaulted selection


    # Determine index for the selectbox
    # This current_selected_id_for_index is the one that selectbox should be set to
    current_selected_id_for_index = st.session_state.get(session_state_key_for_selected_id)
    current_selection_index = 0
    if current_selected_id_for_index and enquiry_options:
        try:
            current_selection_index = list(enquiry_options.values()).index(current_selected_id_for_index)
        except ValueError:
            # This case should ideally be handled by the block above.
            # If it still occurs, default to first and log or handle.
            st.session_state[session_state_key_for_selected_id] = list(enquiry_options.values())[0]
            current_selection_index = 0
            on_selection_change_callback()


    # Store the ID that was selected *before* the selectbox is rendered for the current run
    id_before_selectbox_interaction = st.session_state.get(session_state_key_for_selected_id)

    selectbox_widget_key = f"sb_widget_{session_state_key_for_selected_id}"
    selected_enquiry_label = st_object.selectbox(
        selectbox_label,
        options=list(enquiry_options.keys()),
        index=current_selection_index,
        key=selectbox_widget_key
    )

    # Determine the ID based on the selectbox's current state
    newly_selected_id_from_widget = None
    if selected_enquiry_label and selected_enquiry_label in enquiry_options:
        newly_selected_id_from_widget = enquiry_options[selected_enquiry_label]

    # Compare with the ID *before* this selectbox interaction
    if newly_selected_id_from_widget != id_before_selectbox_interaction:
        st.session_state[session_state_key_for_selected_id] = newly_selected_id_from_widget
        on_selection_change_callback()
        st.rerun()  # Re-run to reflect changes and trigger data loading for the new selection

    return st.session_state.get(session_state_key_for_selected_id), enquiries_list