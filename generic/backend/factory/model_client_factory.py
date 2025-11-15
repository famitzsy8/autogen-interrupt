"""
Model Client Factory

Loads model client configuration from model.yaml and creates the appropriate
client instances (OpenAI or Anthropic) based on the configuration.

This allows parametrized switching between different LLM providers for different
purposes (main conversations vs. state updates).
"""

import os
from pathlib import Path
from typing import Any, Dict, Literal

import yaml

from autogen_core.models import ChatCompletionClient


ModelProvider = Literal["openai", "anthropic"]


class ModelClientConfig:
    """Configuration for a single model client."""

    def __init__(self, provider: ModelProvider, model: str, description: str = ""):
        self.provider = provider
        self.model = model
        self.description = description

    def __repr__(self) -> str:
        return f"ModelClientConfig(provider={self.provider}, model={self.model})"


class ModelClientFactory:
    """Factory for creating model clients from YAML configuration."""

    def __init__(self, config_path: str | None = None):
        """Initialize factory with model configuration.

        Args:
            config_path: Path to model.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to model.yaml in the factory directory
            config_path = str(Path(__file__).parent / "model.yaml")

        self.config_path = config_path
        self._load_config()

    def _load_config(self) -> None:
        """Load model configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Model config not found at: {self.config_path}")

        with open(self.config_path, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data or "model_clients" not in config_data:
            raise ValueError("Invalid model.yaml: must contain 'model_clients' section")

        self._configs: Dict[str, ModelClientConfig] = {}
        for name, cfg in config_data["model_clients"].items():
            self._configs[name] = ModelClientConfig(
                provider=cfg["provider"],
                model=cfg["model"],
                description=cfg.get("description", ""),
            )

    def get_config(self, name: str = "main") -> ModelClientConfig:
        """Get model configuration by name.

        Args:
            name: Configuration name (e.g., "main", "state_updates")

        Returns:
            ModelClientConfig instance

        Raises:
            KeyError: If configuration not found
        """
        if name not in self._configs:
            raise KeyError(
                f"Model config '{name}' not found. Available: {list(self._configs.keys())}"
            )
        return self._configs[name]

    def create_client(self, name: str = "main") -> ChatCompletionClient:
        """Create a model client based on configuration.

        Args:
            name: Configuration name (e.g., "main", "state_updates")

        Returns:
            ChatCompletionClient instance (OpenAI or Anthropic)

        Raises:
            ValueError: If provider is unknown or API key is missing
            KeyError: If configuration not found
        """
        config = self.get_config(name)

        if config.provider == "openai":
            return self._create_openai_client(config)
        elif config.provider == "anthropic":
            return self._create_anthropic_client(config)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

    @staticmethod
    def _create_openai_client(config: ModelClientConfig) -> ChatCompletionClient:
        """Create OpenAI ChatCompletionClient."""
        try:
            from autogen_ext.models.openai import OpenAIChatCompletionClient
        except ImportError:
            raise ImportError("autogen_ext[openai] not installed")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        return OpenAIChatCompletionClient(model=config.model, api_key=api_key)

    @staticmethod
    def _create_anthropic_client(config: ModelClientConfig) -> ChatCompletionClient:
        """Create Anthropic ChatCompletionClient."""
        try:
            from autogen_ext.models.anthropic import AnthropicChatCompletionClient
        except ImportError:
            raise ImportError("autogen_ext[anthropic] not installed")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return AnthropicChatCompletionClient(model=config.model, api_key=api_key)

    def get_all_configs(self) -> Dict[str, ModelClientConfig]:
        """Get all model configurations.

        Returns:
            Dictionary of all configurations
        """
        return self._configs.copy()

    def print_config(self, name: str | None = None) -> None:
        """Print configuration details for debugging.

        Args:
            name: Configuration name. If None, prints all.
        """
        if name:
            cfg = self.get_config(name)
            print(f"Model Config: {name}")
            print(f"  Provider: {cfg.provider}")
            print(f"  Model: {cfg.model}")
            print(f"  Description: {cfg.description}")
        else:
            print("=== All Model Configurations ===")
            for cfg_name, cfg in self._configs.items():
                print(f"\n{cfg_name}:")
                print(f"  Provider: {cfg.provider}")
                print(f"  Model: {cfg.model}")
                print(f"  Description: {cfg.description}")


# Global factory instance (lazy initialized)
_factory: ModelClientFactory | None = None


def get_model_client_factory(
    config_path: str | None = None,
) -> ModelClientFactory:
    """Get or create the global model client factory.

    Args:
        config_path: Path to model.yaml. Only used on first call.

    Returns:
        Global ModelClientFactory instance
    """
    global _factory
    if _factory is None:
        _factory = ModelClientFactory(config_path)
    return _factory


def create_model_client(name: str = "main") -> ChatCompletionClient:
    """Convenience function to create a model client.

    Args:
        name: Configuration name (e.g., "main", "state_updates")

    Returns:
        ChatCompletionClient instance
    """
    factory = get_model_client_factory()
    return factory.create_client(name)
