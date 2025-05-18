import streamlit as st
import os

# Define model options for providers that support multiple models via this UI
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
        "qwen-qwq-32b"
    ],
    "Gemini": [ # Add a list of selectable Gemini models
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
}


def render_sidebar():
    """
    Renders the global AI configuration sidebar.
    Manages 'selected_ai_provider' and 'selected_model_for_provider' in st.session_state.app_state.ai_config.
    """
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter", "Groq"]

    # --- Provider Selection ---
    current_provider_index = 0
    try:
        current_provider_index = ai_provider_options.index(st.session_state.app_state.ai_config.selected_ai_provider)
    except ValueError:
        st.session_state.app_state.ai_config.selected_ai_provider = "OpenRouter" # Default if error
        current_provider_index = ai_provider_options.index("OpenRouter")

    selected_provider = st.sidebar.selectbox(
        "Select AI Provider:",
        options=ai_provider_options,
        index=current_provider_index,
        key="ai_provider_selector_sidebar"
    )

    provider_changed = (selected_provider != st.session_state.app_state.ai_config.selected_ai_provider)
    if provider_changed:
        st.session_state.app_state.ai_config.selected_ai_provider = selected_provider
        st.session_state.app_state.ai_config.selected_model_for_provider = None # Reset model when provider changes

    # --- Model Selection (Dynamic) ---
    active_provider = st.session_state.app_state.ai_config.selected_ai_provider
    model_selection_key = f"model_selector_{active_provider}" # Unique key for selectbox

    if active_provider in PROVIDER_MODEL_OPTIONS:
        available_models = PROVIDER_MODEL_OPTIONS[active_provider]
        
        default_model_env_var = ""
        if active_provider == "OpenRouter":
            default_model_env_var = os.getenv("OPENROUTER_DEFAULT_MODEL")
        elif active_provider == "Groq":
            default_model_env_var = os.getenv("GROQ_DEFAULT_MODEL")
        elif active_provider == "Gemini": # Get default model for Gemini
            default_model_env_var = os.getenv("GOOGLE_DEFAULT_MODEL")


        # Determine current model index for the selectbox
        current_model_index = 0
        # Try to use the model currently in session state if it's valid for the new provider
        if st.session_state.app_state.ai_config.selected_model_for_provider and \
           st.session_state.app_state.ai_config.selected_model_for_provider in available_models:
            current_model_index = available_models.index(st.session_state.app_state.ai_config.selected_model_for_provider)
        # If not, try to use the default from environment variable
        elif default_model_env_var and default_model_env_var in available_models:
            current_model_index = available_models.index(default_model_env_var)
            # Set session state if provider changed or model was None (first time selecting this provider)
            if provider_changed or st.session_state.app_state.ai_config.selected_model_for_provider is None:
                st.session_state.app_state.ai_config.selected_model_for_provider = default_model_env_var
        # If still no valid model, use the first one from the available_models list
        elif available_models:
            current_model_index = 0
            if provider_changed or st.session_state.app_state.ai_config.selected_model_for_provider is None:
                st.session_state.app_state.ai_config.selected_model_for_provider = available_models[0]
        # If no models are available at all (should not happen with current setup)
        else:
            current_model_index = 0
            st.session_state.app_state.ai_config.selected_model_for_provider = None


        selected_model_from_widget = st.sidebar.selectbox(
            f"Select Model for {active_provider}:",
            options=available_models,
            index=current_model_index,
            key=model_selection_key
        )
        if selected_model_from_widget != st.session_state.app_state.ai_config.selected_model_for_provider:
            st.session_state.app_state.ai_config.selected_model_for_provider = selected_model_from_widget
            # Rerun if the model itself changes to ensure consistency in display or dependent logic.
            st.rerun() 
    
    else: # Should not be reached if all providers in ai_provider_options have an entry in PROVIDER_MODEL_OPTIONS
        st.session_state.app_state.ai_config.selected_model_for_provider = None

    # --- Display Current Configuration ---
    st.sidebar.caption(f"Using Provider: {st.session_state.app_state.ai_config.selected_ai_provider}")
    if st.session_state.app_state.ai_config.selected_model_for_provider:
        st.sidebar.caption(f"Using Model: {st.session_state.app_state.ai_config.selected_model_for_provider}")
    
    # Rerun if provider changed to update the model dropdown/display correctly
    if provider_changed:
        st.rerun()