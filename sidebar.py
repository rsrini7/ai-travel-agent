import streamlit as st
import os

# Define model options for providers that support multiple models via this UI
# You can expand these lists
PROVIDER_MODEL_OPTIONS = {
    "OpenRouter": [
        "google/gemma-3-27b-it:free",
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3.3-8b-instruct:free",
        "microsoft/phi-4-reasoning-plus:free",
        "deepseek/deepseek-prover-v2:free"
    ],
    "Groq": [
        "llama3-8b-8192",
        "llama3-70b-8192",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "deepseek-r1-distill-llama-70b",
        "mistral-saba-24b"
    ]
}


def render_sidebar():
    """
    Renders the global AI configuration sidebar.
    Manages 'selected_ai_provider' and 'selected_model_for_provider' in st.session_state.
    """
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter", "Groq"]

    # Initialize session states if not present
    if 'selected_ai_provider' not in st.session_state:
        st.session_state.selected_ai_provider = "OpenRouter"
    if 'selected_model_for_provider' not in st.session_state:
        st.session_state.selected_model_for_provider = None # Will be set based on provider

    # --- Provider Selection ---
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

    provider_changed = (selected_provider != st.session_state.selected_ai_provider)
    if provider_changed:
        st.session_state.selected_ai_provider = selected_provider
        st.session_state.selected_model_for_provider = None # Reset model when provider changes

    # --- Model Selection (Dynamic) ---
    active_provider = st.session_state.selected_ai_provider
    model_selection_key = f"model_selector_{active_provider}" # Unique key for selectbox

    if active_provider in PROVIDER_MODEL_OPTIONS:
        available_models = PROVIDER_MODEL_OPTIONS[active_provider]
        
        # Determine default model for the current provider
        default_model_env_var = ""
        if active_provider == "OpenRouter":
            default_model_env_var = os.getenv("OPENROUTER_DEFAULT_MODEL")
        elif active_provider == "Groq":
            default_model_env_var = os.getenv("GROQ_DEFAULT_MODEL")

        # Use session state for selected model or fallback to env var or first in list
        if st.session_state.selected_model_for_provider and st.session_state.selected_model_for_provider in available_models:
            current_model_index = available_models.index(st.session_state.selected_model_for_provider)
        elif default_model_env_var and default_model_env_var in available_models:
            current_model_index = available_models.index(default_model_env_var)
            st.session_state.selected_model_for_provider = default_model_env_var # Set session state
        elif available_models:
            current_model_index = 0
            st.session_state.selected_model_for_provider = available_models[0] # Set session state
        else: # Should not happen if PROVIDER_MODEL_OPTIONS is well-defined
            current_model_index = 0
            st.session_state.selected_model_for_provider = None


        selected_model = st.sidebar.selectbox(
            f"Select Model for {active_provider}:",
            options=available_models,
            index=current_model_index,
            key=model_selection_key
        )
        if selected_model != st.session_state.selected_model_for_provider:
            st.session_state.selected_model_for_provider = selected_model
            # No st.rerun() needed here typically, as the change will be picked up on next LLM call.
            # However, if other UI elements depend on this immediately, a rerun might be desired.
            # For this use case, it's generally fine.

    else: # For providers like Gemini that have a fixed model in this app
        st.session_state.selected_model_for_provider = None # No specific model selection

    # --- Display Current Configuration ---
    st.sidebar.caption(f"Using Provider: {st.session_state.selected_ai_provider}")
    if st.session_state.selected_model_for_provider:
        st.sidebar.caption(f"Using Model: {st.session_state.selected_model_for_provider}")
    elif st.session_state.selected_ai_provider == "Gemini":
        st.sidebar.caption(f"Gemini Model: gemini-1.5-flash-latest (fixed)")


    # Rerun if provider changed to update the model dropdown correctly
    if provider_changed:
        st.rerun()