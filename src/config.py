from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    apps_script_url: str
    integration_token: str

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def integration_configured(self) -> bool:
        return (
            self.apps_script_url.startswith("https://script.google.com/")
            and self.apps_script_url.rstrip("/").endswith("/exec")
            and len(self.integration_token) >= 32
        )


def _read(name: str, secrets: Mapping[str, Any] | None, default: str = "") -> str:
    try:
        if secrets is not None:
            value = secrets.get(name, "")
            if value is not None and str(value).strip():
                return str(value).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()


def load_settings(secrets: Mapping[str, Any] | None = None) -> Settings:
    return Settings(
        gemini_api_key=_read("GEMINI_API_KEY", secrets),
        gemini_model=_read("GEMINI_MODEL", secrets, "gemini-3.6-flash"),
        apps_script_url=_read("APPS_SCRIPT_WEB_APP_URL", secrets),
        integration_token=_read("INTEGRATION_TOKEN", secrets),
    )
