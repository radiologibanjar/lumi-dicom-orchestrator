"""
Lumi DICOM — Configuration
Copyright © 2026 Lumi DICOM. All rights reserved.

Loads and validates configuration from YAML + environment overrides.
"""

from dataclasses import dataclass, field, fields

import yaml


@dataclass
class DatabaseConfig:
    path: str = "worklist.db"
    wal_mode: bool = True
    auto_vacuum: bool = True


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    cors_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])
    api_keys: list[str] = field(default_factory=lambda: ["lumi-dicom-dev-key"])


@dataclass
class MWLConfig:
    enabled: bool = True
    ae_title: str = "LUMI_DICOM"
    host: str = "0.0.0.0"
    port: int = 11112
    bind: str = "127.0.0.1"
    allowed_aetitles: list[str] = field(default_factory=list)
    max_associations: int = 20
    max_results: int = 1024
    tls_cert: str = ""
    tls_key: str = ""


@dataclass
class MPPSConfig:
    enabled: bool = False
    ae_title: str = "LUMI_MPPS"
    host: str = "0.0.0.0"
    port: int = 11113
    bind: str = "127.0.0.1"
    max_associations: int = 10


@dataclass
class ImageRouteConfig:
    enabled: bool = False
    source_ae: str = "LUMI_ROUTE"
    host: str = "0.0.0.0"
    port: int = 11114
    bind: str = "127.0.0.1"
    destinations: list[dict] = field(default_factory=list)


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class Settings:
    name: str = "Lumi DICOM Orchestrator"
    version: str = "0.1.0"
    environment: str = "development"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    mwl_scp: MWLConfig = field(default_factory=MWLConfig)
    mpps: MPPSConfig = field(default_factory=MPPSConfig)
    image_route: ImageRouteConfig = field(default_factory=ImageRouteConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _build_section(cls, data, *, map_tls: bool = False):
    """Build a config dataclass from one YAML section.

    Keys that are not fields of the dataclass are dropped instead of
    raising ``TypeError`` (the YAML sections legitimately carry extra
    keys such as the nested ``tls:`` block). When ``map_tls`` is set and
    TLS is enabled, ``tls.cert_file``/``tls.key_file`` become
    ``tls_cert``/``tls_key`` as the SCP classes expect.
    """
    if not isinstance(data, dict):
        data = {}
    allowed = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in allowed and k != "tls"}
    if map_tls:
        tls = data.get("tls")
        if isinstance(tls, dict) and tls.get("enabled", False):
            kwargs["tls_cert"] = tls.get("cert_file", "") or ""
            kwargs["tls_key"] = tls.get("key_file", "") or ""
    return cls(**kwargs)


def load_settings(config_path: str) -> Settings:
    """Load Lumi DICOM settings from a YAML config file.

    Component sections are read from the top level of the file, with an
    optional ``lumi_dicom:`` block merged over them — the same layout
    ``__main__.load_config`` consumes at runtime.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    lumi_section = dict(raw.get("lumi_dicom") or {})
    cfg = {k: v for k, v in raw.items() if k != "lumi_dicom"}
    cfg.update(lumi_section)

    def section(name: str) -> dict:
        value = cfg.get(name)
        return value if isinstance(value, dict) else {}

    return Settings(
        name=cfg.get("name", "Lumi DICOM Orchestrator"),
        version=cfg.get("version", "0.1.0"),
        environment=cfg.get("environment", "development"),
        database=_build_section(DatabaseConfig, section("database")),
        api=_build_section(APIConfig, section("api")),
        mwl_scp=_build_section(MWLConfig, section("mwl_scp"), map_tls=True),
        mpps=_build_section(MPPSConfig, section("mpps"), map_tls=True),
        image_route=_build_section(ImageRouteConfig, section("image_route")),
        logging=_build_section(LoggingConfig, section("logging")),
    )
