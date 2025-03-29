# tests/test_integrations/llms/test_service.py
"""
Tests for the LLM integration service.

This module tests the main service class for LLM integration, including
initialization, configuration, and client communication.
"""

from unittest.mock import MagicMock, patch

import pytest

from quackcore.errors import QuackIntegrationError
from quackcore.integrations.core import BaseIntegrationService
from quackcore.integrations.core.results import IntegrationResult, ConfigResult
from quackcore.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quackcore.integrations.llms.service import LLMIntegration
from tests.test_integrations.llms.mocks.clients import MockClient


class TestLLMService:
    """Tests for the LLM integration service."""

    @pytest.fixture
    def llm_service(self) -> LLMIntegration:
        """Create a properly initialized LLM integration service."""
        # Create a service
        service = LLMIntegration()

        # Skip actual file loading
        with patch("quackcore.fs.service.get_file_info") as mock_file_info:
            mock_file_info.return_value.success = True
            mock_file_info.return_value.exists = True

            with patch("quackcore.fs.service.read_yaml") as mock_read_yaml:
                mock_read_yaml.return_value = ConfigResult(
                    success=True,
                    content={
                        "default_provider": "openai",
                        "timeout": 60,
                        "openai": {"api_key": "test-key"}
                    }
                )

                # Set the config directly
                service.config = {
                    "default_provider": "openai",
                    "timeout": 60,
                    "openai": {"api_key": "test-key"}
                }

                # Mark as initialized to skip initialization
                service._initialized = True

                # Set a mock client
                service.client = MagicMock()

                return service

    def test_init(self) -> None:
        """Test initializing the LLM integration service."""
        # Test with default parameters
        service = LLMIntegration()
        assert service.provider is None
        assert service.model is None
        assert service.api_key is None
        assert service.client is None
        assert service._initialized is False

        # Test with custom parameters
        with patch("quackcore.fs.service.get_file_info") as mock_file_info:
            # No need to check for file existence when config_path is explicitly provided
            mock_file_info.return_value.success = True
            mock_file_info.return_value.exists = True

            service = LLMIntegration(
                provider="anthropic",
                model="claude-3-opus",
                api_key="test-key",
                config_path="config.yaml",
                log_level=20,
            )
            assert service.provider == "anthropic"
            assert service.model == "claude-3-opus"
            assert service.api_key == "test-key"
            # config_path might be resolved, so don't test exact equality
            assert "config.yaml" in service.config_path
            assert service.logger.level == 20

    def test_name_and_version(self, llm_service: LLMIntegration) -> None:
        """Test the name and version properties."""
        assert llm_service.name == "LLM"
        assert llm_service.version == "1.0.0"  # This should match what's in the code

    def test_initialize(self, llm_service: LLMIntegration) -> None:
        """Test initializing the LLM integration."""
        # Test successful initialization
        with patch(
            "quackcore.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = llm_service.initialize()

            assert result.success is True
            assert llm_service._initialized is True
            assert llm_service.client == mock_client

            # Should call get_llm_client with config values
            mock_get_client.assert_called_once()
            assert mock_get_client.call_args[1]["provider"] == "openai"
            assert mock_get_client.call_args[1]["api_key"] == "test-key"

        # Test base initialization failure
        with patch(
            "quackcore.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_init:
            mock_init.return_value = IntegrationResult(
                success=False,
                error="Base initialization failed",
            )

            result = llm_service.initialize()

            assert result.success is False
            assert "Base initialization failed" in result.error
            assert llm_service._initialized is False

        # Test config extraction failure
        with patch.object(llm_service, "_extract_config") as mock_extract:
            mock_extract.side_effect = QuackIntegrationError("Config extraction failed")

            result = llm_service.initialize()

            assert result.success is False
            assert "Config extraction failed" in result.error
            assert llm_service._initialized is False

        # Test client initialization failure
        with patch(
            "quackcore.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_get_client.side_effect = QuackIntegrationError(
                "Client initialization failed"
            )

            result = llm_service.initialize()

            assert result.success is False
            assert "Client initialization failed" in result.error
            assert llm_service._initialized is False

    def test_extract_config(self, llm_service: LLMIntegration) -> None:
        """Test extracting and validating the LLM configuration."""
        # Test successful extraction
        config = llm_service._extract_config()
        assert config == llm_service.config

        # Test with missing config and mock provider responses
        # Create a new service to avoid state from previous test
        test_service = LLMIntegration()
        test_service.config = None

        # Mock the config provider
        with patch(
                "quackcore.integrations.llms.config.LLMConfigProvider") as MockProvider:
            # Create a mock provider instance
            mock_provider_instance = MagicMock()
            MockProvider.return_value = mock_provider_instance

            # Set up for success case
            mock_provider_instance.load_config.return_value = ConfigResult(
                success=True,
                content={"default_provider": "anthropic", "timeout": 30}
            )

            config1 = test_service._extract_config()
            assert config1["default_provider"] == "anthropic"

            # Clear and reset for failure case
            mock_provider_instance.reset_mock()
            mock_provider_instance.load_config.return_value = ConfigResult(
                success=False,
                error="Config not found"
            )
            mock_provider_instance.get_default_config.return_value = {
                "default_provider": "mock",
                "timeout": 10
            }

            # Need a new service to avoid cached result
            test_service2 = LLMIntegration()
            test_service2.config = None

            config2 = test_service2._extract_config()
            assert config2["default_provider"] == "mock"

    def test_chat(self, llm_service: LLMIntegration) -> None:
        """Test the chat method."""
        # Set up mock client
        mock_client = MockClient(responses=["Test response"])
        llm_service.client = mock_client

        # Test successful chat
        messages = [
            ChatMessage(role=RoleType.USER, content="Test message"),
        ]
        options = LLMOptions(temperature=0.5)

        result = llm_service.chat(messages, options)

        assert result.success is True
        assert result.content == "Test response"

        # The uninitialized test needs to bypass the auto-initialize behavior
        # Create a test-specific service with specific behavior
        with patch(
                "quackcore.integrations.llms.service.LLMIntegration.initialize") as mock_init:
            # Make initialize return a failure without auto-retry
            mock_init.return_value = IntegrationResult(
                success=False,
                error="LLM integration not initialized"
            )

            uninitialized_service = LLMIntegration()
            uninitialized_service._initialized = False

            result = uninitialized_service.chat(messages)

            assert result.success is False
            assert "not initialized" in result.error

    def test_count_tokens(self, llm_service: LLMIntegration) -> None:
        """Test the count_tokens method."""
        # Set up mock client
        mock_client = MockClient(token_counts=[42])
        llm_service.client = mock_client

        # Test successful token counting
        messages = [
            ChatMessage(role=RoleType.USER, content="Test message"),
        ]

        result = llm_service.count_tokens(messages)

        assert result.success is True
        assert result.content == 42

        # For uninitialized test, create a service with specific behavior
        with patch(
                "quackcore.integrations.llms.service.LLMIntegration.initialize") as mock_init:
            mock_init.return_value = IntegrationResult(
                success=False,
                error="LLM integration not initialized"
            )

            uninitialized_service = LLMIntegration()
            uninitialized_service._initialized = False

            result = uninitialized_service.count_tokens(messages)

            assert result.success is False
            assert "not initialized" in result.error

    def test_get_client(self, llm_service: LLMIntegration) -> None:
        """Test the get_client method."""
        # Set up mock client
        mock_client = MockClient()
        llm_service.client = mock_client
        llm_service._initialized = True

        # Test successful client retrieval
        client = llm_service.get_client()
        assert client == mock_client

        # Test not initialized
        llm_service._initialized = False
        with pytest.raises(QuackIntegrationError) as excinfo:
            llm_service.get_client()

        assert "LLM client not initialized" in str(excinfo.value)
