import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Search order for .env configuration files
USER_HOME_ENV = Path.home() / ".parley" / ".env"
APPDATA_DIR = Path(os.getenv("APPDATA", "")) / "Parley" if os.getenv("APPDATA") else None
APPDATA_ENV = APPDATA_DIR / ".env" if APPDATA_DIR else None
LOCAL_ENV = Path.cwd() / ".env"

# Load in order of precedence: local .env > ~/.parley/.env > %APPDATA%/Parley/.env
for env_path in [LOCAL_ENV, USER_HOME_ENV, APPDATA_ENV]:
    if env_path and env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)

def get_persistent_env_path() -> Path:
    """Returns the persistent user .env file path."""
    target_dir = Path.home() / ".parley"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / ".env"

class Settings(BaseSettings):
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    DEEPGRAM_MODEL: str = os.getenv("DEEPGRAM_MODEL", "nova-3")
    DEEPGRAM_UTTERANCE_END_MS: int = int(os.getenv("DEEPGRAM_UTTERANCE_END_MS", "5000"))

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")

    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")

    ANALYSIS_INTERVAL_SECONDS: int = int(os.getenv("ANALYSIS_INTERVAL_SECONDS", "15"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

def reload_settings():
    """Reloads settings from environment and persistent files."""
    global settings
    for env_path in [LOCAL_ENV, USER_HOME_ENV, APPDATA_ENV]:
        if env_path and env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=True)
    settings = Settings()
    return settings

def save_api_keys(
    deepgram_key: Optional[str] = None,
    deepseek_key: Optional[str] = None,
    exa_key: Optional[str] = None,
):
    """Saves API keys to ~/.parley/.env and reloads the active runtime settings."""
    env_file = get_persistent_env_path()
    existing_lines = []
    if env_file.is_file():
        existing_lines = env_file.read_text(encoding="utf-8").splitlines()

    env_map = {}
    for line in existing_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_map[k.strip()] = v.strip()

    if deepgram_key is not None:
        env_map["DEEPGRAM_API_KEY"] = deepgram_key
        os.environ["DEEPGRAM_API_KEY"] = deepgram_key
    if deepseek_key is not None:
        env_map["DEEPSEEK_API_KEY"] = deepseek_key
        os.environ["DEEPSEEK_API_KEY"] = deepseek_key
    if exa_key is not None:
        env_map["EXA_API_KEY"] = exa_key
        os.environ["EXA_API_KEY"] = exa_key

    new_content = "\n".join(f"{k}={v}" for k, v in env_map.items()) + "\n"
    env_file.write_text(new_content, encoding="utf-8")
    return reload_settings()

