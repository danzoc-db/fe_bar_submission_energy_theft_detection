import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .._metadata import app_name, app_slug

project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / ".env"
env_local_file = project_root / ".env.local"

if env_file.exists():
    load_dotenv(dotenv_path=env_file)
if env_local_file.exists():
    load_dotenv(dotenv_path=env_local_file, override=True)


class AppConfig(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=env_file,
        env_prefix=f"{app_slug.upper()}_",
        extra="ignore",
    )
    app_name: str = Field(default=app_name)
    databricks_config_profile: str = Field(
        default="DEFAULT",
        validation_alias="DATABRICKS_CONFIG_PROFILE",
    )
    sql_warehouse_id: str = Field(
        default="",
        validation_alias="SQL_WAREHOUSE_ID",
    )
    ai_gateway_endpoint: str = Field(
        default="energy-theft-openai-gateway",
        validation_alias="AI_GATEWAY_ENDPOINT",
    )
    gemini_gateway_endpoint: str = Field(
        default="energy-theft-gemini-gateway",
        validation_alias="GEMINI_GATEWAY_ENDPOINT",
    )
    openai_gateway_endpoint: str = Field(
        default="energy-theft-openai-gateway",
        validation_alias="OPENAI_GATEWAY_ENDPOINT",
    )
    llama_gateway_endpoint: str = Field(
        default="energy-theft-llama-gateway",
        validation_alias="LLAMA_GATEWAY_ENDPOINT",
    )
    mas_endpoint: str = Field(
        default="",
        validation_alias="MAS_ENDPOINT",
    )
    genie_space_id: str = Field(
        default="",
        validation_alias="GENIE_SPACE_ID",
    )
    catalog: str = Field(default="", validation_alias="CATALOG")
    schema_name: str = Field(
        default="energy_theft_protection", validation_alias="SCHEMA_NAME"
    )

    @property
    def workspace_url(self) -> str:
        """Derive workspace URL from DATABRICKS_HOST (set automatically in deployed
        apps) or from the SDK profile. Returns empty string if unavailable."""
        host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
