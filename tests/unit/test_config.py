from harness.core.config import HarnessSettings, settings


def test_config_defaults() -> None:
    """Verify default configurations in HarnessSettings."""
    assert settings.environment in ["development", "production", "staging"]
    assert settings.primary_model == "azure/gpt-4o"
    assert settings.max_retries >= 1
    assert settings.max_session_cost_usd > 0.0
    assert settings.max_iterations >= 1
    assert settings.redact_pii is True


def test_config_custom_instantiation() -> None:
    """Verify custom settings overrides."""
    custom = HarnessSettings(
        primary_model="anthropic/claude-3-5-sonnet",
        max_session_cost_usd=2.50,
        max_iterations=15,
        environment="production",
    )
    assert custom.primary_model == "anthropic/claude-3-5-sonnet"
    assert custom.max_session_cost_usd == 2.50
    assert custom.max_iterations == 15
    assert custom.environment == "production"
