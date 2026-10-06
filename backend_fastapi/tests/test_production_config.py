import logging

import pytest

from app.core.config import Settings

GOOD_SECRET = "a" * 8 + "f3c9d2e1b47a6058" * 3  # 56 chars, no placeholder markers


def make_settings(**overrides) -> Settings:
    base = dict(
        environment="production",
        secret_key=GOOD_SECRET,
        cors_allowed_origins="https://app.example.com",
        use_mock_chatbot=False,
        kyc_stub_auto_verify=False,
        razorpay_key_id="rzp_live_x",
        razorpay_key_secret="secret",
        razorpay_webhook_secret="whsec",
        database_url="postgresql+asyncpg://airtasker:S0meStr0ngPass@db:5432/airtasker",
    )
    base.update(overrides)
    # _env_file=None so a developer's local backend_fastapi/.env can't change the result.
    return Settings(_env_file=None, **base)


def test_safe_production_config_has_no_errors_or_warnings():
    errors, warnings = make_settings().production_config_problems()
    assert errors == []
    assert warnings == []


@pytest.mark.parametrize("environment", ["development", "dev", "test", "staging"])
def test_guard_is_a_noop_outside_production(environment):
    # Placeholder secret + wildcard CORS is the normal local/CI/staging setup; it must keep working.
    s = make_settings(environment=environment, secret_key="change-this-secret-in-production", cors_allowed_origins="*")
    assert s.production_config_problems() == ([], [])
    s.enforce_production_config()  # must not raise


@pytest.mark.parametrize(
    "secret",
    [
        "change-this-secret-in-production",  # Settings default
        "staging-change-me-use-long-random-string",  # docker-compose.staging.yml default
        "docker-dev-change-me-use-long-random-string",  # backend_fastapi/.env.docker.example
        "replace-with-openssl-rand-hex-32-output" + "0" * 8,  # deploy/aws.env.example / oracle.env.example
        "replace-with-64-char-random-string",  # .env.production.example
        "ci-test-secret-do-not-use-in-production",  # CI workflow value
        "short",  # too short
        "",  # unset
    ],
)
def test_placeholder_or_short_secret_key_is_an_error(secret):
    errors, _ = make_settings(secret_key=secret).production_config_problems()
    assert any("SECRET_KEY" in e for e in errors)


def test_wildcard_cors_is_an_error():
    errors, _ = make_settings(cors_allowed_origins="*").production_config_problems()
    assert any("CORS_ALLOWED_ORIGINS" in e for e in errors)


def test_wildcard_hidden_in_a_list_is_still_an_error():
    errors, _ = make_settings(cors_allowed_origins="https://app.example.com, *").production_config_problems()
    assert any("CORS_ALLOWED_ORIGINS" in e for e in errors)


def test_explicit_cors_origins_are_accepted():
    s = make_settings(cors_allowed_origins="https://app.example.com,https://www.example.com")
    errors, _ = s.production_config_problems()
    assert errors == []


def test_environment_match_is_case_and_whitespace_insensitive():
    s = make_settings(environment=" Production ", secret_key="short")
    errors, _ = s.production_config_problems()
    assert errors


def test_enforce_raises_and_names_every_problem():
    s = make_settings(secret_key="short", cors_allowed_origins="*")
    with pytest.raises(RuntimeError) as exc:
        s.enforce_production_config()
    message = str(exc.value)
    assert "SECRET_KEY" in message
    assert "CORS_ALLOWED_ORIGINS" in message


def test_kyc_stub_auto_verify_warns_but_does_not_block(caplog):
    s = make_settings(kyc_provider="stub", kyc_stub_auto_verify=True)
    errors, warnings = s.production_config_problems()
    assert errors == []
    assert any("KYC_STUB_AUTO_VERIFY" in w for w in warnings)
    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        s.enforce_production_config()  # warnings only — must not raise
    assert "KYC_STUB_AUTO_VERIFY" in caplog.text


def test_real_kyc_provider_does_not_trigger_auto_verify_warning():
    s = make_settings(kyc_provider="signzy", kyc_stub_auto_verify=True)
    _, warnings = s.production_config_problems()
    assert not any("KYC_STUB_AUTO_VERIFY" in w for w in warnings)


def test_other_risky_but_non_fatal_settings_only_warn():
    s = make_settings(
        use_mock_chatbot=True,
        database_url="postgresql+asyncpg://postgres:postgres@db:5432/airtasker",
        razorpay_key_id=None,
        razorpay_webhook_secret=None,
    )
    errors, warnings = s.production_config_problems()
    assert errors == []
    joined = " ".join(warnings)
    assert "USE_MOCK_CHATBOT" in joined
    assert "postgres:postgres" in joined
    assert "RAZORPAY_KEY_ID" in joined
    assert "RAZORPAY_WEBHOOK_SECRET" in joined
