"""
Metric registry — auto-discovery, tenant-aware loading, and dependency ordering.

Metrics register themselves by calling register_metric() at module level.
The aggregator calls get_enabled_metrics() to get only the metrics that
are enabled in the active configuration.

Plugin discovery hierarchy:
  1. Core plugins:   app/ml/analysis/metrics/           (platform-owned)
  2. Tenant plugins: app/ml/analysis/tenant_plugins/<company_id>/  (company-owned)

Configuration resolution:
  1. config/<company_id>/enabled_metrics.yaml   (tenant-specific)
  2. config/<company_id>/weights.yaml           (tenant-specific)
  3. config/default/enabled_metrics.yaml        (platform default)
  4. config/default/weights.yaml                (platform default)
  5. config/metrics.yaml                        (legacy fallback)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .interfaces import BaseMetric, EnhancedMetric

logger = logging.getLogger(__name__)

# ── Global registries ─────────────────────────────────────────────────────────
# Core plugins: always loaded
_registry: dict[str, "BaseMetric"] = {}
# Tenant plugins: keyed by company_id → {metric_key → instance}
_tenant_registry: dict[str, dict[str, "BaseMetric"]] = {}

# ── Path resolution ──────────────────────────────────────────────────────────
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_LEGACY_CONFIG_PATH = _BACKEND_ROOT / "config" / "metrics.yaml"
_DEFAULT_CONFIG_DIR = _BACKEND_ROOT / "config" / "default"
_TENANT_PLUGINS_DIR = Path(__file__).parent / "tenant_plugins"


def register_metric(metric: "BaseMetric") -> "BaseMetric":
    """
    Register a core metric instance.  Called at module import time by each
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


def register_tenant_metric(
    company_id: str, metric: "BaseMetric"
) -> "BaseMetric":
    """
    Register a tenant-specific metric.

    Tenant plugins are isolated per company_id and only loaded when
    that company's analysis runs.
    """
    key = metric.name.lower().replace(" ", "_")
    if company_id not in _tenant_registry:
        _tenant_registry[company_id] = {}
    _tenant_registry[company_id][key] = metric
    logger.info(
        f"[metrics] Registered tenant metric: {metric.name} "
        f"(company={company_id}, key={key})"
    )
    return metric


# ── Configuration loading ─────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    """Load a YAML file safely.  Returns empty dict on failure."""
    if not path.exists():
        return {}
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[metrics] Failed to read {path}: {e}")
        return {}


def _resolve_config(filename: str, company_id: str | None = None) -> dict:
    """
    Resolve a config file with tenant fallback:
      1. config/<company_id>/<filename>  (if company_id provided)
      2. config/default/<filename>
      3. config/metrics.yaml             (legacy fallback for enabled_metrics)
    """
    # Tenant-specific
    if company_id:
        tenant_path = _BACKEND_ROOT / "config" / company_id / filename
        cfg = _load_yaml(tenant_path)
        if cfg:
            logger.info(f"[metrics] Loaded tenant config: {tenant_path}")
            return cfg

    # Platform default
    default_path = _DEFAULT_CONFIG_DIR / filename
    cfg = _load_yaml(default_path)
    if cfg:
        logger.info(f"[metrics] Loaded default config: {default_path}")
        return cfg

    # Legacy fallback (only for enabled_metrics)
    if filename in ("enabled_metrics.yaml", "metrics.yaml"):
        legacy = _load_yaml(_LEGACY_CONFIG_PATH)
        if legacy:
            logger.info(f"[metrics] Loaded legacy config: {_LEGACY_CONFIG_PATH}")
            return legacy

    return {}


def load_enabled_metrics_config(
    company_id: str | None = None,
) -> list[str]:
    """
    Load the list of enabled metric keys for the active tenant.

    Falls back to all registered metrics if no config exists.
    """
    cfg = _resolve_config("enabled_metrics.yaml", company_id)
    enabled = cfg.get("enabled_metrics", None)
    if enabled is None:
        # Try legacy config key
        cfg = _resolve_config("metrics.yaml", company_id)
        enabled = cfg.get("enabled_metrics", None)
    if enabled is None:
        logger.info("[metrics] No enabled_metrics config — enabling all")
        return list(_registry.keys())
    return enabled


def load_weights_config(
    company_id: str | None = None,
) -> dict[str, float]:
    """
    Load metric weights for the active tenant.

    Returns {metric_key: weight} dict.
    Falls back to equal weights if no config exists.
    """
    cfg = _resolve_config("weights.yaml", company_id)
    weights = cfg.get("weights", {})
    if not weights:
        logger.debug("[metrics] No weights config — using equal weights")
    return weights


def load_competency_config(
    company_id: str | None = None,
) -> dict[str, Any]:
    """
    Load competency definitions for the active tenant.

    Returns the full competencies YAML structure.
    """
    return _resolve_config("competencies.yaml", company_id)


# ── Metric retrieval ──────────────────────────────────────────────────────────


def get_enabled_metrics(
    company_id: str | None = None,
) -> list["BaseMetric"]:
    """
    Return only the metrics that are enabled for the active tenant.

    Combines core metrics and tenant-specific metrics, filtered by
    the enabled_metrics config.
    """
    enabled = load_enabled_metrics_config(company_id)

    # Core metrics
    result = [m for key, m in _registry.items() if key in enabled]
    skipped = [key for key in _registry if key not in enabled]

    # Tenant metrics (if company_id specified)
    if company_id and company_id in _tenant_registry:
        tenant_metrics = _tenant_registry[company_id]
        for key, m in tenant_metrics.items():
            if key in enabled:
                result.append(m)

    if skipped:
        logger.debug(f"[metrics] Skipped disabled metrics: {skipped}")

    # Sort by dependency order
    result = _dependency_sort(result)

    return result


def get_all_metrics() -> list["BaseMetric"]:
    """Return all registered core metrics regardless of config."""
    return list(_registry.values())


def get_metric_by_name(name: str) -> "BaseMetric | None":
    """Look up a metric by its registry key or display name."""
    key = name.lower().replace(" ", "_")
    return _registry.get(key)


# ── Dependency ordering ───────────────────────────────────────────────────────


def _get_requires(metric: "BaseMetric") -> dict[str, int]:
    """
    Get versioned requirements from a metric, or empty dict for V1 plugins.
    """
    return getattr(metric, "requires", {}) or {}


def _dependency_sort(metrics: list["BaseMetric"]) -> list["BaseMetric"]:
    """
    Sort metrics by their declared dependencies.

    Metrics with no requirements run first.  Metrics that depend on
    preprocessing outputs (e.g. STAR, behaviour_evidence) run later.

    This is a stable topological sort — if two metrics have equal
    dependency depth, their original order is preserved.
    """
    def _dep_depth(m: "BaseMetric") -> int:
        reqs = _get_requires(m)
        return len(reqs)

    return sorted(metrics, key=_dep_depth)


# ── Plugin discovery ──────────────────────────────────────────────────────────


def discover_metrics() -> None:
    """
    Import all core metric modules in app/ml/analysis/metrics/ to trigger
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


def discover_tenant_metrics(company_id: str) -> None:
    """
    Discover and load metrics for a specific tenant.

    Scans app/ml/analysis/tenant_plugins/<company_id>/ for plugin files
    and registers them in the tenant-specific registry.

    Tenant plugins are completely isolated:
      - They don't modify core plugins
      - They don't access other tenants' plugins
      - They fail safely — a tenant plugin crash never affects core
    """
    import importlib

    tenant_dir = _TENANT_PLUGINS_DIR / company_id
    if not tenant_dir.exists():
        logger.debug(
            f"[metrics] No tenant plugins for company '{company_id}'"
        )
        return

    count = 0
    for path in sorted(tenant_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = (
            f"app.ml.analysis.tenant_plugins.{company_id}.{path.stem}"
        )
        try:
            importlib.import_module(module_name)
            count += 1
        except Exception as e:
            logger.warning(
                f"[metrics] Failed to load tenant metric {module_name}: {e}"
            )

    logger.info(
        f"[metrics] Tenant discovery for '{company_id}': "
        f"{count} module(s) loaded"
    )

