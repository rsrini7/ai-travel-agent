import os
import unittest
from unittest.mock import patch, MagicMock

# Assuming ChatOpenAI is imported in the module we are testing like:
# from langchain_openai import ChatOpenAI
# If it's imported as `from langchain_openai.chat_models import ChatOpenAI`, the patch path needs to reflect that.
# For now, we'll assume `src.llm.llm_providers.ChatOpenAI` is the correct path to mock.

from src.llm.llm_providers import get_llm_instance
from src.models import AIConfigState, AppSessionState # Use AppSessionState

# Mock Streamlit's session state
# No longer needed as we will mock st.session_state directly in tests or via mock_st argument.

@patch('src.llm.llm_providers.st') # Mocking streamlit (st) module used in llm_providers
class TestTogetherAIProvider(unittest.TestCase):

    def setUp(self):
        # Basic AIConfigState, specific tests will override parts of this
        self.mock_ai_config = AIConfigState(
            # provider="TogetherAI", # Provider is passed to get_llm_instance directly
            selected_model_for_provider=None,
            temperature=0.5,
            max_tokens=150
        )
        # This will be assigned to mock_st.session_state.app_state in each test
        self.mock_app_session_state = AppSessionState(ai_config=self.mock_ai_config)

    @patch.dict(os.environ, {"TOGETHERAI_API_KEY": "test_together_key"})
    @patch('src.llm.llm_providers.ChatOpenAI') # Mocking ChatOpenAI where it's used
    def test_get_llm_instance_togetherai_default_model(self, mock_chat_openai_class, mock_st):
        """Test TogetherAI initialization with default model."""
        mock_st.session_state.app_state = self.mock_app_session_state
        
        llm_instance = get_llm_instance(provider="TogetherAI", ai_conf=self.mock_ai_config)

        mock_chat_openai_class.assert_called_once()
        args, kwargs = mock_chat_openai_class.call_args
        self.assertEqual(kwargs['model'], "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free") # Default model
        self.assertEqual(kwargs['openai_api_key'], "test_together_key")
        self.assertEqual(kwargs['base_url'], "https://api.together.xyz/v1")
        self.assertEqual(kwargs['temperature'], 0.5)
        self.assertEqual(kwargs['max_tokens'], 150)
        self.assertIsNotNone(llm_instance)

    @patch.dict(os.environ, {"TOGETHERAI_API_KEY": "test_together_key"})
    @patch('src.llm.llm_providers.ChatOpenAI')
    def test_get_llm_instance_togetherai_selected_model(self, mock_chat_openai_class, mock_st):
        """Test TogetherAI initialization with a user-selected model."""
        self.mock_ai_config.selected_model_for_provider = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
        # Re-create AppSessionState with updated ai_config
        mock_st.session_state.app_state = AppSessionState(ai_config=self.mock_ai_config)

        llm_instance = get_llm_instance(provider="TogetherAI", ai_conf=self.mock_ai_config)

        mock_chat_openai_class.assert_called_once()
        args, kwargs = mock_chat_openai_class.call_args
        self.assertEqual(kwargs['model'], "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free")
        self.assertEqual(kwargs['openai_api_key'], "test_together_key")
        self.assertEqual(kwargs['base_url'], "https://api.together.xyz/v1")
        self.assertEqual(kwargs['temperature'], 0.5)
        self.assertEqual(kwargs['max_tokens'], 150)
        self.assertIsNotNone(llm_instance)

    @patch.dict(os.environ, {"TOGETHERAI_API_KEY": "test_together_key", "TOGETHERAI_DEFAULT_MODEL": "env_default_model"})
    @patch('src.llm.llm_providers.ChatOpenAI')
    def test_get_llm_instance_togetherai_env_default_model(self, mock_chat_openai_class, mock_st):
        """Test TogetherAI initialization with default model from environment variable."""
        # Ensure no specific model is selected in session state
        self.mock_ai_config.selected_model_for_provider = None
        # Re-create AppSessionState with updated ai_config
        mock_st.session_state.app_state = AppSessionState(ai_config=self.mock_ai_config)
        
        llm_instance = get_llm_instance(provider="TogetherAI", ai_conf=self.mock_ai_config)

        mock_chat_openai_class.assert_called_once()
        args, kwargs = mock_chat_openai_class.call_args
        self.assertEqual(kwargs['model'], "env_default_model") 
        self.assertEqual(kwargs['openai_api_key'], "test_together_key")
        self.assertEqual(kwargs['base_url'], "https://api.together.xyz/v1")
        self.assertIsNotNone(llm_instance)

    @patch.dict(os.environ, {}, clear=True) # Ensure TOGETHERAI_API_KEY is not set
    def test_get_llm_instance_togetherai_missing_key(self, mock_st):
        """Test TogetherAI initialization raises ValueError if API key is missing."""
        mock_st.session_state.app_state = self.mock_app_session_state
        
        with self.assertRaises(ValueError) as context:
            get_llm_instance(provider="TogetherAI", ai_conf=self.mock_ai_config)
        self.assertIn("TOGETHERAI_API_KEY not found", str(context.exception))

if __name__ == '__main__':
    unittest.main()
