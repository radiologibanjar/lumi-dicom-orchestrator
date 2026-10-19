"""
Lumi DICOM Orchestrator — Entry Point
Copyright © 2026 Lumi DICOM. All rights reserved.

Usage:
    python -m lumi_dicom start --config config/default.yaml
    lumi-dicom start --config config/default.yaml
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn
import yaml

# Ensure src/ is on path when running without install
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from lumi_dicom import __version__
from lumi_dicom.api.server import create_app
from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.dicom.mpps import MPPSSCP
from lumi_dicom.dicom.mwl_scp import MWLSCP
from lumi_dicom.workers.image_router import ImageRouter

logger = logging.getLogger("lumi-dicom")


def _parse_env_value(val: str):
    """Parse env var string into int/bool/list/str."""
    # bool
    if val.lower() in ("true", "yes", "1"):
        return True
    if val.lower() in ("false", "no", "0"):
        return False
    # int
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    # comma-separated list
    if "," in val:
        return [v.strip() for v in val.split(",") if v.strip()]
    return val


def load_config(config_path: str) -> dict:
    """Load Lumi DICOM config from YAML file.

    The YAML has a ``lumi_dicom:`` section for global settings and separate
    top-level sections for each component (database, api, mwl_scp, etc.).
    This function merges them into a single flat dict.

    Environment variable overrides use ``__`` as nesting separator:
    ``LUMI_DICOM_API__PORT=18765`` → ``cfg["api"]["port"] = 18765``.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Merge lumi_dicom section with top-level sections
    lumi_global = raw.get("lumi_dicom", {})
    cfg = {k: v for k, v in raw.items() if k != "lumi_dicom"}
    cfg.update(lumi_global)

    # Walk all nested keys and check for env overrides
    def _walk(d, prefix):
        for key, val in d.items():
            env_key = f"{prefix}{key.upper()}"
            if isinstance(val, dict):
                _walk(val, f"{env_key}__")
            else:
                env_val = os.environ.get(env_key)
                if env_val is not None:
                    d[key] = _parse_env_value(env_val)

    _walk(cfg, "LUMI_DICOM_")
    return cfg


def _resolve_tls(tls_cfg) -> tuple[str, str]:
    """Resolve TLS cert/key paths from a config section.

    Returns ("", "") when TLS is disabled or no paths are configured,
    which both SCP classes treat as "run without TLS".
    """
    if not isinstance(tls_cfg, dict) or not tls_cfg.get("enabled", False):
        return "", ""
    return tls_cfg.get("cert_file", "") or "", tls_cfg.get("key_file", "") or ""


async def run_orchestrator(cfg: dict):
    """Run all Lumi DICOM services concurrently."""
    # ── Database ────────────────────────────────────────────────────────────
    db_cfg = cfg.get("database", {})
    db_path = db_cfg.get("path", "worklist.db")
    db_manager = DatabaseManager(db_path=db_path)
    db_manager.init()
    logger.info("Lumi DICOM database ready: %s", db_path)

    # ── Inbound API ─────────────────────────────────────────────────────────
    api_cfg = cfg.get("api", {})
    app = create_app(db_manager=db_manager, config=cfg)

    uvi_config = uvicorn.Config(
        app,
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 8765),
        log_level="info",
    )
    uvi_server = uvicorn.Server(uvi_config)
    logger.info("Lumi DICOM Inbound API starting on %s:%s",
                api_cfg.get("host", "0.0.0.0"), api_cfg.get("port", 8765))

    # ── DICOM Services ──────────────────────────────────────────────────────
    dicom_tasks = []

    mwl_cfg = cfg.get("mwl_scp", {})
    if mwl_cfg.get("enabled", False):
        mwl_tls_cert, mwl_tls_key = _resolve_tls(mwl_cfg.get("tls"))
        mwl_scp = MWLSCP(
            db_manager=db_manager,
            ae_title=mwl_cfg.get("ae_title", "LUMI_DICOM"),
            host=mwl_cfg.get("host", "0.0.0.0"),
            port=mwl_cfg.get("port", 11112),
            bind=mwl_cfg.get("bind", "127.0.0.1"),
            allowed_aetitles=mwl_cfg.get("allowed_aetitles", []),
            max_associations=mwl_cfg.get("max_associations", 20),
            max_results=mwl_cfg.get("max_results", 1024),
            tls_cert=mwl_tls_cert,
            tls_key=mwl_tls_key,
        )
        dicom_tasks.append(asyncio.create_task(mwl_scp.serve()))
        logger.info("Lumi DICOM MWL SCP starting on %s:%s (AE: %s)",
                    mwl_cfg.get("bind", "127.0.0.1"),
                    mwl_cfg.get("port", 11112),
                    mwl_cfg.get("ae_title", "LUMI_DICOM"))

    mpps_cfg = cfg.get("mpps", {})
    if mpps_cfg.get("enabled", False):
        mpps_tls_cert, mpps_tls_key = _resolve_tls(mpps_cfg.get("tls"))
        mpps_scp = MPPSSCP(
            db_manager=db_manager,
            ae_title=mpps_cfg.get("ae_title", "LUMI_MPPS"),
            host=mpps_cfg.get("host", "0.0.0.0"),
            port=mpps_cfg.get("port", 11113),
            bind=mpps_cfg.get("bind", "127.0.0.1"),
            tls_cert=mpps_tls_cert,
            tls_key=mpps_tls_key,
        )
        dicom_tasks.append(asyncio.create_task(mpps_scp.serve()))
        logger.info("Lumi DICOM MPPS SCP starting on %s:%s",
                    mpps_cfg.get("bind", "127.0.0.1"),
                    mpps_cfg.get("port", 11113))

    route_cfg = cfg.get("image_route", {})
    if route_cfg.get("enabled", False):
        router = ImageRouter(
            db_manager=db_manager,
            source_ae=route_cfg.get("source_ae", "LUMI_ROUTE"),
            destinations=route_cfg.get("destinations", []),
        )
        dicom_tasks.append(asyncio.create_task(router.serve()))
        logger.info("Lumi DICOM Image Route starting (AE: %s)",
                    route_cfg.get("source_ae", "LUMI_ROUTE"))

    # ── Run all ─────────────────────────────────────────────────────────────
    all_tasks = [asyncio.create_task(uvi_server.serve())] + dicom_tasks

    # Graceful shutdown on SIGINT/SIGTERM
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Lumi DICOM shutdown signal received")
        stop_event.set()

    # Windows doesn't support add_signal_handler — use signal.signal instead
    use_signal_handlers = True
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _handle_signal)
    except NotImplementedError:
        use_signal_handlers = False
        logger.debug("Lumi DICOM: add_signal_handler not supported, using signal.signal")

    if not use_signal_handlers:
        import signal as _signal
        for sig in (_signal.SIGINT, _signal.SIGTERM):
            _signal.signal(sig, lambda *_: _handle_signal())

    # Wait for shutdown signal
    await stop_event.wait()

    # Cancel all tasks
    for task in all_tasks:
        task.cancel()
    await asyncio.gather(*all_tasks, return_exceptions=True)

    logger.info("Lumi DICOM Orchestrator stopped")


def main():
    """Lumi DICOM CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lumi-dicom",
        description="Lumi DICOM Orchestrator — DICOM radiology workflow orchestrator",
    )
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Start Lumi DICOM orchestrator")
    start_p.add_argument("--config", default="config/default.yaml",
                         help="Path to YAML config file")

    args = parser.parse_args()

    if args.command == "start":
        cfg = load_config(args.config)
        logging.basicConfig(
            level=getattr(logging, cfg.get("logging", {}).get("level", "INFO")),
            format=cfg.get("logging", {}).get(
                "format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ),
            datefmt=cfg.get("logging", {}).get("date_format", "%Y-%m-%d %H:%M:%S"),
        )
        logger.info("Starting Lumi DICOM Orchestrator v%s", __version__)
        try:
            asyncio.run(run_orchestrator(cfg))
        except KeyboardInterrupt:
            logger.info("Lumi DICOM stopped by user")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
