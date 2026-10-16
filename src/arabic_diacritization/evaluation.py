"""Read-only access to stored experiment metrics (not re-evaluation)."""

from ._reference_engine import get_metrics

__all__ = ["get_metrics"]
