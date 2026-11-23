import pytest
from pydantic import ValidationError

from app.config import BASE_DIR, _env_files, get_settings
from app.llm import create_chat_model

REQUIRED_VARIABLES = [
    "CHAT_MODEL",
    "EMBEDDING_MODEL",
    "TAVILY_API_KEY",
    "LLM_TEMPERATURE",
]


def test_config_sin_api_key_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        get_settings()


@pytest.mark.parametrize("variable", REQUIRED_VARIABLES)
def test_config_exige_cada_campo_sin_default(
    variable: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ValidationError):
        get_settings()


def test_config_usa_defaults_seguros() -> None:
    settings = get_settings()

    assert settings.nest_base_url == "http://localhost:3001"
    assert settings.chroma_dir.name == "chroma"
    assert settings.knowledge_dir.name == "knowledge"
    assert settings.retrieval_top_k == 4
    assert settings.http_timeout_seconds == 10.0
    assert settings.llm_timeout_seconds == 45.0
    assert settings.llm_max_retries == 2


def test_env_por_defecto_es_solo_el_del_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENT_ENV_FILE", raising=False)

    assert _env_files() == (BASE_DIR / ".env",)


def test_create_chat_model_usa_el_modelo_configurado() -> None:
    settings = get_settings()

    model = create_chat_model(settings)

    assert model.model == f"models/{settings.chat_model}"
