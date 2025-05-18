import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

# Load environment variables specific to LLM providers
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
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", 
            google_api_key=api_key,
            request_options={"timeout": 120} # This is valid for ChatGoogleGenerativeAI
        )
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
            # REMOVED request_options={"timeout": 120} from here
            # model_kwargs can be used for model-specific params, e.g., model_kwargs={"max_tokens": 1000}
        )
    elif provider == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        model_name = os.getenv("GROQ_DEFAULT_MODEL", "llama3-8b-8192") 
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