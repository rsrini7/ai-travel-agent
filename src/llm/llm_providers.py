# src/llm/llm_providers.py:
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

def get_llm_instance(provider: str, ai_conf): # Added ai_conf parameter
    """
    Returns an LLM instance based on the specified provider, selected model,
    and advanced settings from session state.
    """
    selected_model = ai_conf.selected_model_for_provider
    temperature = ai_conf.temperature
    max_tokens_from_state = ai_conf.max_tokens

    # Prepare common LLM parameters
    llm_params = {}
    if temperature is not None:
        llm_params['temperature'] = temperature
    # Note: max_tokens parameter name can vary, but LangChain often standardizes it.

    if provider == "Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        model_for_api_call = selected_model
        if not model_for_api_call: 
            model_for_api_call = os.getenv("GOOGLE_DEFAULT_MODEL", "gemini-1.5-flash-latest")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Gemini. Check .env file.")
        
        # Gemini specific parameter name for max tokens is 'max_output_tokens'
        if max_tokens_from_state is not None:
            llm_params['max_output_tokens'] = max_tokens_from_state
        
        gemini_model_kwargs = {"request_options": {"timeout": 120}}

        print(f"LLM_PROVIDERS.PY: Initializing Gemini with model: {model_for_api_call}, Params: {llm_params}, ModelKwargs: {gemini_model_kwargs}")
        return ChatGoogleGenerativeAI(
            model=model_for_api_call,
            google_api_key=api_key,
            model_kwargs=gemini_model_kwargs, # For non-generation params like timeout
            **llm_params # Spread temperature, max_output_tokens
        )
    
    elif provider == "OpenRouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model_name = selected_model
        if not model_name:
            model_name = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-3.5-turbo")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found for OpenRouter. Check .env file.")
        
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000")
        app_title = os.getenv("OPENROUTER_APP_TITLE", "AI Travel Quotation")
        headers = {"HTTP-Referer": http_referer, "X-Title": app_title}
        
        # ChatOpenAI (used by OpenRouter) typically uses 'max_tokens'
        if max_tokens_from_state is not None:
            llm_params['max_tokens'] = max_tokens_from_state
        
        print(f"LLM_PROVIDERS.PY: Initializing OpenRouter with model: {model_name}, Params: {llm_params}")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers,
            **llm_params # Spread temperature, max_tokens
        )
        
    elif provider == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        model_name = selected_model
        if not model_name:
            model_name = os.getenv("GROQ_DEFAULT_MODEL", "llama3-8b-8192")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found for Groq. Check .env file.")
        
        # ChatGroq standard parameter for max tokens is 'max_tokens'
        # The warning previously indicated that 'max_output_tokens' was moved to model_kwargs.
        # We should use the direct parameter if available.
        if max_tokens_from_state is not None:
            llm_params['max_tokens'] = max_tokens_from_state
            # Remove 'max_output_tokens' if it was incorrectly added to llm_params before
            if 'max_output_tokens' in llm_params:
                del llm_params['max_output_tokens']


        print(f"LLM_PROVIDERS.PY: Initializing Groq with model: {model_name}, Params: {llm_params}")
        return ChatGroq(
            groq_api_key=api_key,
            model_name=model_name,
            **llm_params # Spread temperature, max_tokens
        )

    elif provider == "TogetherAI":
        api_key = os.getenv("TOGETHERAI_API_KEY")
        model_name = selected_model
        if not model_name:
            model_name = os.getenv("TOGETHERAI_DEFAULT_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free")
        if not api_key:
            raise ValueError("TOGETHERAI_API_KEY not found for TogetherAI. Check .env file.")

        # ChatOpenAI (used by TogetherAI) typically uses 'max_tokens'
        if max_tokens_from_state is not None:
            llm_params['max_tokens'] = max_tokens_from_state
        
        print(f"LLM_PROVIDERS.PY: Initializing TogetherAI with model: {model_name}, Params: {llm_params}")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url="https://api.together.xyz/v1",
            **llm_params # Spread temperature, max_tokens
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}. Supported: 'Gemini', 'OpenRouter', 'Groq', 'TogetherAI'.")