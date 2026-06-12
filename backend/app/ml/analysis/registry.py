"""
Metric registry — auto-discovery and YAML-based enable/disable.

Metrics register themselves by calling register_metric() at module level.
The aggregator calls get_enabled_metrics() to get only the metrics that
are enabled in config/metrics.yaml.

Adding a new metric:
  1. Create app/ml/analysis/metrics/your_metric.py
  2. Call register_metric(YourMetricInstance()) at the bottom
  3. Add "your_metric" to config/metrics.yaml under enabled_metrics
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import BaseMetric

logger = logging.getLogger(__name__)

# Global registry: metric_key (lowercase_underscored) → BaseMetric instance
_registry: dict[str, "BaseMetric"] = {}

# Path to YAML config — lives at backend/config/metrics.yaml
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "metrics.yaml"


def register_metric(metric: "BaseMetric") -> "BaseMetric":
    """
    Register a metric instance. Called at module import time by each
    metric plugin file.

    The registry key is derived from the metric's name:
      "Confidence" → "confidence"
      "Emotional Stability" → "emotional_stability"
    """
    key = metric.name.lower().replace(" ", "_")
    if key in _registry:
        logger.warning(
            f"[metrics] Metric '{key}' already registered — "
            f"overwriting with {metric.__class__.__name__}"
        )
    _registry[key] = metric
    logger.info(f"[metrics] Registered metric: {metric.name} (key={key})")
    return metric


def _load_enabled() -> list[str]:
    """
    Read enabled_metrics from YAML config.
    Returns all registered metric keys if no config file exists.
    """
    if not _CONFIG_PATH.exists():
        logger.info(
            f"[metrics] No config at {_CONFIG_PATH} — "
            f"all {len(_registry)} registered metrics enabled"
        )
        return list(_registry.keys())

    try:
        import yaml
        with open(_CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        enabled = cfg.get("enabled_metrics", list(_registry.keys()))
        logger.info(f"[metrics] Config loaded: {len(enabled)} metrics enabled")
        return enabled
    except Exception as e:
        logger.warning(f"[metrics] Failed to read config: {e} — enabling all")
        return list(_registry.keys())


def get_enabled_metrics() -> list["BaseMetric"]:
    """Return only the metrics that are enabled in config."""
    enabled = _load_enabled()
    result = [m for key, m in _registry.items() if key in enabled]
    skipped = [key for key in _registry if key not in enabled]
    if skipped:
        logger.debug(f"[metrics] Skipped disabled metrics: {skipped}")
    return result


def get_all_metrics() -> list["BaseMetric"]:
    """Return all registered metrics regardless of config."""
    return list(_registry.values())


def get_metric_by_name(name: str) -> "BaseMetric | None":
    """Look up a metric by its registry key or display name."""
    key = name.lower().replace(" ", "_")
    return _registry.get(key)


def discover_metrics() -> None:
    """
    Import all metric modules in app/ml/analysis/metrics/ to trigger
    their register_metric() calls.

    Called once at server startup (main.py lifespan).
    """
    import importlib

    metrics_dir = Path(__file__).parent / "metrics"
    if not metrics_dir.exists():
        logger.warning(f"[metrics] Metrics directory not found: {metrics_dir}")
        return

    count = 0
    for path in sorted(metrics_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"app.ml.analysis.metrics.{path.stem}"
        try:
            importlib.import_module(module_name)
            count += 1
        except Exception as e:
            logger.warning(f"[metrics] Failed to load {module_name}: {e}")

    logger.info(
        f"[metrics] Discovery complete: {count} module(s) loaded, "
        f"{len(_registry)} metric(s) registered"
    )
