"""Disk-based cache implementation for bundles."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amplifier_foundation.bundle import Bundle


class DiskCache:
    """Disk-based cache for bundles.

    Persists bundle metadata to filesystem for cross-session caching.
    Apps MUST provide cache_dir - foundation doesn't decide where to cache.

    Simple JSON serialization of bundle data. Supports optional TTL-based
    expiration — entries older than ttl_seconds are treated as cache misses.
    """

    def __init__(self, cache_dir: Path, ttl_seconds: float | None = None) -> None:
        """Initialize disk cache.

        Args:
            cache_dir: Directory for storing cached bundles.
                       Apps decide this location (e.g., ~/.myapp/cache/bundles/).
            ttl_seconds: Optional time-to-live in seconds. When set, cached
                         entries older than this are treated as misses.
                         None means no expiration (default).
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path_for(self, cache_path: Path) -> Path:
        """Get the metadata file path for a cache entry.

        Args:
            cache_path: Path to the cache data file.

        Returns:
            Path to the corresponding .meta.json file.
        """
        return cache_path.with_suffix(".meta.json")

    def _read_meta(self, cache_path: Path) -> dict[str, object] | None:
        """Read metadata for a cache entry.

        Args:
            cache_path: Path to the cache data file.

        Returns:
            Metadata dict, or None if missing or invalid.
        """
        meta_path = self._meta_path_for(cache_path)
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))  # type: ignore[return-value]
        except (json.JSONDecodeError, OSError):
            return None

    def _is_entry_stale(self, cache_path: Path) -> bool:
        """Check if a cache entry is past TTL based on its metadata.

        Args:
            cache_path: Path to the cache data file.

        Returns:
            True if TTL is set and the entry is older than TTL.
        """
        if self.ttl_seconds is None:
            return False

        meta = self._read_meta(cache_path)
        if meta is None:
            # No metadata — treat as stale if TTL is configured,
            # since we can't verify age.
            return True

        created_at = meta.get("created_at")
        if not isinstance(created_at, (int, float)):
            return True

        return (time.time() - created_at) > self.ttl_seconds

    def _cache_key_to_path(self, key: str) -> Path:
        """Convert cache key to filesystem path.

        Args:
            key: Cache key (URI or bundle name).

        Returns:
            Path to cache file.
        """
        # Hash the key to create safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        # Keep first part of key for debugging
        safe_prefix = "".join(c if c.isalnum() or c in "-_" else "_" for c in key[:30])
        return self.cache_dir / f"{safe_prefix}-{key_hash}.json"

    def get(self, key: str) -> Bundle | None:
        """Get a cached bundle.

        Returns None (cache miss) if the entry doesn't exist, is invalid,
        or has exceeded its TTL.

        Args:
            key: Cache key.

        Returns:
            Cached Bundle, or None if not cached, invalid, or stale.
        """
        cache_path = self._cache_key_to_path(key)
        if not cache_path.exists():
            return None

        # TTL check — stale entries are treated as misses
        if self._is_entry_stale(cache_path):
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            # Import here to avoid circular import
            from amplifier_foundation.bundle import Bundle

            bundle = Bundle.from_dict(data)
            # Restore instruction which from_dict doesn't set
            if "instruction" in data:
                bundle.instruction = data["instruction"]
            return bundle
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            # Invalid cache entry - remove it
            cache_path.unlink(missing_ok=True)
            self._meta_path_for(cache_path).unlink(missing_ok=True)
            return None

    def set(self, key: str, bundle: Bundle) -> None:
        """Cache a bundle.

        Args:
            key: Cache key.
            bundle: Bundle to cache.
        """
        self._ensure_cache_dir()
        cache_path = self._cache_key_to_path(key)

        # Serialize bundle to dict in Bundle.from_dict format
        # Context paths need to be converted to strings for JSON
        context_dict = {name: str(path) for name, path in bundle.context.items()}

        data = {
            "bundle": {
                "name": bundle.name,
                "version": bundle.version,
                "description": bundle.description,
            },
            "includes": bundle.includes,
            "session": bundle.session,
            "providers": bundle.providers,
            "tools": bundle.tools,
            "hooks": bundle.hooks,
            "agents": bundle.agents,
            "context": context_dict,
            "instruction": bundle.instruction,
        }

        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Write metadata alongside the cached data
        meta = {"created_at": time.time(), "key": key}
        meta_path = self._meta_path_for(cache_path)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def is_stale(self, key: str) -> bool:
        """Check if a cached entry is stale (past its TTL).

        Args:
            key: Cache key to check.

        Returns:
            True if the entry exists and is past its TTL, False otherwise.
            Always returns False when no TTL is configured.
        """
        cache_path = self._cache_key_to_path(key)
        if not cache_path.exists():
            return False
        return self._is_entry_stale(cache_path)

    def refresh(self, key: str) -> None:
        """Clear a stale entry so it can be re-populated.

        Removes both the cached data and its metadata file.
        No-op if the entry doesn't exist or isn't stale.

        Args:
            key: Cache key to refresh.
        """
        cache_path = self._cache_key_to_path(key)
        if not cache_path.exists():
            return
        if not self._is_entry_stale(cache_path):
            return
        cache_path.unlink(missing_ok=True)
        self._meta_path_for(cache_path).unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cached bundles and their metadata."""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)

    def __contains__(self, key: str) -> bool:
        """Check if key is cached."""
        return self._cache_key_to_path(key).exists()
