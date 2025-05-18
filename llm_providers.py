import os
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

def get_llm_instance(provider: str):
    """
    Returns an LLM instance based on the specified provider and selected model from session state.
    """
    selected_model = st.session_state.get('selected_model_for_provider') # Get model from session state

    if provider == "Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Gemini. Check .env file.")
        # Gemini uses a fixed model in this app configuration
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=api_key,
            request_options={"timeout": 120}
        )
    elif provider == "OpenRouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        # Use selected_model if available, else fallback to env var
        model_name = selected_model if selected_model else os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-3.5-turbo")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found for OpenRouter. Check .env file.")
        
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000")
        app_title = os.getenv("OPENROUTER_APP_TITLE", "AI Travel Quotation")
        headers = {"HTTP-Referer": http_referer, "X-Title": app_title}
        
        print(f"LLM_PROVIDERS.PY: Initializing OpenRouter with model: {model_name}")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers
        )
    elif provider == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        # Use selected_model if available, else fallback to env var
        model_name = selected_model if selected_model else os.getenv("GROQ_DEFAULT_MODEL", "llama3-8b-8192")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found for Groq. Check .env file.")
        
        print(f"LLM_PROVIDERS.PY: Initializing Groq with model: {model_name}")
        return ChatGroq(
            groq_api_key=api_key,
            model_name=model_name,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}. Supported: 'Gemini', 'OpenRouter', 'Groq'.")