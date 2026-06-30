# app/ml/analysis/tenant_plugins — Company-specific metric plugins
#
# Each subdirectory represents a tenant (company):
#   tenant_plugins/<company_id>/plugin.py
#
# Tenant plugins:
#   - Receive ReadonlySessionContext (cannot modify shared state)
#   - Return MetricResult or EnhancedMetricResult
#   - Are completely isolated from other tenants
#   - Fail safely — a crash never affects core plugins
