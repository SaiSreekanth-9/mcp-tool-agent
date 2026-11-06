"""Central configuration for mcp-tool-agent. Values come from environment variables / .env.

Demo mode needs no API key: planning is rule-based by default. The optional LLM
planner (see src/agent.py) only activates when OPENAI_API_KEY is set, and its
langchain / dotenv imports are lazy, so this module must never fail at import
time if those packages are missing.
"""
import os

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional in demo mode
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    audit_log: str = os.getenv("AUDIT_LOG", "audit.log")
    manifest_path: str = os.getenv("MANIFEST_PATH", "tools/manifest.json")
    data_dir: str = os.getenv("DATA_DIR", "data")
    chat_model: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")


settings = Settings()
