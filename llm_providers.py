import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Load environment variables specific to LLM providers
# This will be called when this module is imported.
# app.py also calls load_dotenv(), which is fine.
if load_dotenv():
    print("LLM_PROVIDERS.PY: .env file loaded successfully.")
else:
    print("LLM_PROVIDERS.PY: .env file not found.")

def get_llm_instance(provider: str):
    """
    Returns an LLM instance based on the specified provider.
    """
    if provider == "Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Gemini. Check .env file.")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key)
    elif provider == "OpenRouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model_name = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-flash-1.5")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found for OpenRouter. Check .env file.")
        
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000")
        app_title = os.getenv("OPENROUTER_APP_TITLE", "AI Travel Quotation")
        headers = {"HTTP-Referer": http_referer, "X-Title": app_title}
        
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}. Supported providers are 'Gemini', 'OpenRouter'.")