# src/ui/sidebar.py
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
    "Gemini": [
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro"
    ],
    "TogetherAI": [
        "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
        # Add other TogetherAI models here if needed
    ]
}

def render_sidebar():
    """
    Renders the global AI configuration sidebar.
    Manages AI provider, model, and advanced settings in st.session_state.app_state.ai_config.
    """
    st.sidebar.subheader("⚙️ AI Configuration")
    ai_provider_options = ["Gemini", "OpenRouter", "Groq", "TogetherAI"] # Added TogetherAI
    ai_conf = st.session_state.app_state.ai_config # Shorthand for session state config

    # --- Provider Selection ---
    current_provider_index = 0
    try:
        current_provider_index = ai_provider_options.index(ai_conf.selected_ai_provider)
    except ValueError:
        ai_conf.selected_ai_provider = "OpenRouter"
        current_provider_index = ai_provider_options.index("OpenRouter")

    selected_provider = st.sidebar.selectbox(
        "Select AI Provider:",
        options=ai_provider_options,
        index=current_provider_index,
        key="ai_provider_selector_sidebar"
    )

    provider_changed = (selected_provider != ai_conf.selected_ai_provider)
    if provider_changed:
        ai_conf.selected_ai_provider = selected_provider
        ai_conf.selected_model_for_provider = None # Reset model
        # When provider changes, reset advanced settings to their Pydantic defaults
        # by re-initializing the relevant part of the config or setting them explicitly.
        # Here, we can rely on the Pydantic default values when next accessed if they are None
        # or set them explicitly if we want specific defaults upon provider change beyond pydantic's.
        # For simplicity, we'll let them be picked up by the Pydantic defaults if needed,
        # or the user can adjust. The widgets below will use current values or Pydantic defaults.
        # A more robust reset might involve:
        # default_temp = AIConfigState().temperature
        # default_max_tokens = AIConfigState().max_tokens
        # ai_conf.temperature = default_temp
        # ai_conf.max_tokens = default_max_tokens

    # --- Model Selection (Dynamic) ---
    active_provider = ai_conf.selected_ai_provider
    model_selection_key = f"model_selector_{active_provider}"

    if active_provider in PROVIDER_MODEL_OPTIONS:
        available_models = PROVIDER_MODEL_OPTIONS[active_provider]
        default_model_env_var = ""
        if active_provider == "OpenRouter": default_model_env_var = os.getenv("OPENROUTER_DEFAULT_MODEL")
        elif active_provider == "Groq": default_model_env_var = os.getenv("GROQ_DEFAULT_MODEL")
        elif active_provider == "Gemini": default_model_env_var = os.getenv("GOOGLE_DEFAULT_MODEL")
        elif active_provider == "TogetherAI": default_model_env_var = os.getenv("TOGETHERAI_DEFAULT_MODEL")

        current_model_index = 0
        if ai_conf.selected_model_for_provider and ai_conf.selected_model_for_provider in available_models:
            current_model_index = available_models.index(ai_conf.selected_model_for_provider)
        elif default_model_env_var and default_model_env_var in available_models:
            current_model_index = available_models.index(default_model_env_var)
            if provider_changed or ai_conf.selected_model_for_provider is None:
                ai_conf.selected_model_for_provider = default_model_env_var
        elif available_models:
            current_model_index = 0
            if provider_changed or ai_conf.selected_model_for_provider is None:
                ai_conf.selected_model_for_provider = available_models[0]
        else:
            current_model_index = 0
            ai_conf.selected_model_for_provider = None

        selected_model_from_widget = st.sidebar.selectbox(
            f"Select Model for {active_provider}:",
            options=available_models,
            index=current_model_index,
            key=model_selection_key
        )
        if selected_model_from_widget != ai_conf.selected_model_for_provider:
            ai_conf.selected_model_for_provider = selected_model_from_widget
            st.rerun()
    else:
        ai_conf.selected_model_for_provider = None

    # --- Advanced Settings ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Advanced Settings")

    # Temperature (0.0 to 2.0, some providers like Gemini might prefer 0.0 to 1.0)
    # The Pydantic model has default=0.7, ge=0.0, le=2.0
    temp_to_display = float(ai_conf.temperature if ai_conf.temperature is not None else AIConfigState().temperature)
    
    new_temp = st.sidebar.slider(
        "Temperature:",
        min_value=0.0,
        max_value=2.0, # General max
        value=temp_to_display,
        step=0.1,
        key=f"temperature_slider_{active_provider}",
        help="Lower for more deterministic outputs, higher for more creative/random. Default: 0.7"
    )
    if new_temp != ai_conf.temperature:
        ai_conf.temperature = new_temp
        # No rerun needed, will be picked up by next LLM call.
        # However, if this change should invalidate a cache (like quotation graph), a rerun might be forced elsewhere or here.
        # For now, assume dependent functions check this value directly.

    # Max Tokens (Output)
    # Pydantic model has default=None (provider default), ge=1
    max_tokens_to_display = ai_conf.max_tokens # This can be None
    
    new_max_tokens_input = st.sidebar.number_input(
        "Max Tokens (Output):",
        min_value=1,
        value=max_tokens_to_display if max_tokens_to_display is not None else None, # Pass None to number_input to show placeholder
        step=50, # Or 1, or 100, depending on common use
        key=f"max_tokens_input_{active_provider}",
        help="Max tokens to generate. Leave blank for provider default.",
        placeholder="Provider default" # This placeholder shows if value is None
    )
    # Convert to int if a value is provided, else keep as None
    new_max_tokens_val = int(new_max_tokens_input) if new_max_tokens_input is not None else None
    
    if new_max_tokens_val != ai_conf.max_tokens:
        ai_conf.max_tokens = new_max_tokens_val
        # Similar to temperature, no immediate rerun unless explicitly needed for cache invalidation.

    # --- Display Current Configuration ---
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Provider: {ai_conf.selected_ai_provider}")
    if ai_conf.selected_model_for_provider:
        st.sidebar.caption(f"Model: {ai_conf.selected_model_for_provider}")
    st.sidebar.caption(f"Temperature: {ai_conf.temperature if ai_conf.temperature is not None else 'Default (0.7)'}")
    st.sidebar.caption(f"Max Tokens: {ai_conf.max_tokens if ai_conf.max_tokens is not None else 'Provider Default'}")
    
    if provider_changed: # This rerun handles provider/model changes primarily.
        st.rerun()