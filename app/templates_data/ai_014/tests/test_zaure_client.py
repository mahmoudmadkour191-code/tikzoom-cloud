import unittest
import sys
import types
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

fake_openai = types.ModuleType('openai')
fake_openai.AzureOpenAI = MagicMock()
sys.modules.setdefault('openai', fake_openai)

fake_mysql_conn = types.ModuleType('db.MySqlConn')
fake_mysql_conn.config = {
    "AI": {
        "CHAT_TOKEN": "chat-token",
        "CHAT_BASE": "https://example.openai.azure.com",
        "CHAT_VERSION": "2024-05-01-preview",
        "IMAGE_TOKEN": "image-token",
        "IMAGE_AUTH_TYPE": "auto",
        "IMAGE_BEARER_TOKEN": "",
        "IMAGE_BASE": "https://example.openai.azure.com",
        "IMAGE_VERSION": "2025-04-01-preview",
        "IMAGE_MODEL": "gpt-image-1",
        "MODEL": "gpt-4o"
    }
}
sys.modules.setdefault('db.MySqlConn', fake_mysql_conn)

from ai.azure import AzureAIClient
from ai.azure import config as azure_config


class TestAzureAIClient(unittest.TestCase):
    def setUp(self):
        azure_config["AI"]["IMAGE_AUTH_TYPE"] = "auto"
        azure_config["AI"]["IMAGE_BEARER_TOKEN"] = ""

    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_returns_decoded_bytes(self, MockAzureOpenAI, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": [{"b64_json": "aGVsbG8="}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = AzureAIClient()

        result = client.generate_image("fox")

        self.assertEqual(result, b"hello")
        mock_urlopen.assert_called_once()

    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_uses_api_key_header_first(self, MockAzureOpenAI, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": [{"b64_json": "aGVsbG8="}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = AzureAIClient()

        client.generate_image("fox")

        http_request = mock_urlopen.call_args[0][0]
        self.assertEqual(http_request.headers["Api-key"], "image-token")

    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_falls_back_to_bearer_after_403(self, MockAzureOpenAI, mock_urlopen):
        forbidden = HTTPError(
            url='https://example.openai.azure.com',
            code=403,
            msg='Forbidden',
            hdrs=None,
            fp=MagicMock(read=MagicMock(return_value=b'{"error": "forbidden"}'))
        )
        success_response = MagicMock()
        success_response.read.return_value = b'{"data": [{"b64_json": "aGVsbG8="}]}'

        def side_effect(http_request, timeout=60):
            auth_header = http_request.headers.get("Authorization")
            if auth_header:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = success_response
                return context_manager
            raise forbidden

        mock_urlopen.side_effect = side_effect

        client = AzureAIClient()

        result = client.generate_image("fox")

        self.assertEqual(result, b"hello")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_bearer_mode_sends_authorization_header(self, MockAzureOpenAI, mock_urlopen):
        azure_config["AI"]["IMAGE_AUTH_TYPE"] = "bearer"
        azure_config["AI"]["IMAGE_BEARER_TOKEN"] = "aad-token"

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": [{"b64_json": "aGVsbG8="}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = AzureAIClient()
        client.generate_image("fox")

        http_request = mock_urlopen.call_args[0][0]
        self.assertEqual(http_request.headers["Authorization"], "Bearer aad-token")

    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_authentication_type_disabled_message(self, MockAzureOpenAI, mock_urlopen):
        azure_config["AI"]["IMAGE_AUTH_TYPE"] = "api_key"

        auth_disabled = HTTPError(
            url='https://example.openai.azure.com',
            code=403,
            msg='Forbidden',
            hdrs=None,
            fp=MagicMock(read=MagicMock(return_value=b'{"error":{"code":"AuthenticationTypeDisabled"}}'))
        )
        mock_urlopen.side_effect = auth_disabled

        client = AzureAIClient()

        with self.assertRaises(ValueError) as context:
            client.generate_image("fox")

        self.assertIn("IMAGE_AUTH_TYPE", str(context.exception))

    @patch('ai.azure.AzureOpenAI')
    def test_chat_completions(self, MockAzureOpenAI):
        # Mock the AzureOpenAI client and its methods
        mock_client = MockAzureOpenAI.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message={"role": "assistant", "content": "Recursion is fun."})]
        mock_client.chat.completions.create.return_value = mock_response

        # Create an instance of AzureAIClient
        client = AzureAIClient()

        # Define test inputs
        messages = [{"role": "user", "content": "Write a haiku about recursion in programming."}]

        # Call the chat_completions method and collect results
        result = client.chat_completions(messages)

        # Verify the results
        self.assertEqual(result.choices[0].message["content"], "Recursion is fun.")


if __name__ == '__main__':
    unittest.main()
