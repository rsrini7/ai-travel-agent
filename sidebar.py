import streamlit as st
import os

def render_sidebar():
    """
    Renders the global AI configuration sidebar.
    Manages the 'selected_ai_provider' in st.session_state.
    """
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter", "Groq"]

    if 'selected_ai_provider' not in st.session_state:
        st.session_state.selected_ai_provider = "OpenRouter" 

    current_provider_index = 0
    try:
        current_provider_index = ai_provider_options.index(st.session_state.selected_ai_provider)
    except ValueError:
        st.session_state.selected_ai_provider = "OpenRouter"
        current_provider_index = ai_provider_options.index("OpenRouter")


    selected_provider = st.sidebar.selectbox(
        "Select AI Provider:",
        options=ai_provider_options,
        index=current_provider_index,
        key="ai_provider_selector_sidebar"
    )

    if selected_provider != st.session_state.selected_ai_provider:
        st.session_state.selected_ai_provider = selected_provider
        st.rerun()

    st.sidebar.caption(f"Using: {st.session_state.selected_ai_provider}")
    if st.session_state.selected_ai_provider == "OpenRouter":
        openrouter_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemma-3-27b-it:free")
        st.sidebar.caption(f"OpenRouter Model: {openrouter_model}")
    elif st.session_state.selected_ai_provider == "Groq":
        # UPDATED DEFAULT MODEL DISPLAYED HERE
        groq_model = os.getenv("GROQ_DEFAULT_MODEL", "llama3-8b-8192") 
        st.sidebar.caption(f"Groq Model: {groq_model}")
    elif st.session_state.selected_ai_provider == "Gemini":
        st.sidebar.caption(f"Gemini Model: gemini-1.5-flash-latest")