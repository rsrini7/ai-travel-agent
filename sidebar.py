import streamlit as st
import os

def render_sidebar():
    """
    Renders the global AI configuration sidebar.
    Manages the 'selected_ai_provider' in st.session_state.
    """
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter"]

    # Initialize session state for AI provider if not already present
    # This is defensive, as app.py should initialize it.
    if 'selected_ai_provider' not in st.session_state:
        st.session_state.selected_ai_provider = "OpenRouter" # Default

    current_provider_index = 0
    try:
        current_provider_index = ai_provider_options.index(st.session_state.selected_ai_provider)
    except ValueError:
        # If the stored provider is somehow invalid, default to OpenRouter
        st.session_state.selected_ai_provider = "OpenRouter"
        current_provider_index = ai_provider_options.index("OpenRouter")


    selected_provider = st.sidebar.selectbox(
        "Select AI Provider:",
        options=ai_provider_options,
        index=current_provider_index,
        key="ai_provider_selector_sidebar" # Keeping the key consistent
    )

    if selected_provider != st.session_state.selected_ai_provider:
        st.session_state.selected_ai_provider = selected_provider
        # Important: Rerun the app to reflect the provider change immediately
        # This ensures that any components depending on the provider update.
        st.rerun()

    st.sidebar.caption(f"Using: {st.session_state.selected_ai_provider}")
    if st.session_state.selected_ai_provider == "OpenRouter":
        openrouter_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5")
        st.sidebar.caption(f"OpenRouter Model: {openrouter_model}")
        