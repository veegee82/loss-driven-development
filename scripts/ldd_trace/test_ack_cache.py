"""Tests for the v0.13.x Fix 3 — autonomy ack-cache."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from ldd_trace.ack_cache import (
    AckCache,
    Grant,
    SUPPORTED_SCOPES,
    family_hash,
)


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AckCache:
    """Isolated AckCache rooted in a tmp directory — does not touch ~/.claude."""
    monkeypatch.setenv("LDD_ACK_ROOT", str(tmp_path / "ldd-acks"))
    return AckCache()


class TestGrantAndCheck:
    def test_grant_then_check_valid(self, cache: AckCache) -> None:
        cache.grant("billing-schema-changes")
        assert cache.check("billing-schema-changes") is True

    def test_check_absent_family(self, cache: AckCache) -> None:
        assert cache.check("never-granted") is False

    def test_family_hash_deterministic(self) -> None:
        assert family_hash("foo") == family_hash("foo")
        assert family_hash("foo") != family_hash("bar")

    def test_grant_persists_as_json(self, cache: AckCache) -> None:
        cache.grant("x")
        files = list(cache.root.glob("*.json"))
        assert len(files) == 1
        body = json.loads(files[0].read_text())
        assert body["family"] == "x"
        assert body["scope"] == ["inventive"]
        assert "hmac" in body
        assert len(body["hmac"]) == 64  # sha256 hex


class TestScope:
    def test_default_scope_is_inventive(self, cache: AckCache) -> None:
        cache.grant("x")
        assert cache.check("x", scope="inventive") is True

    def test_check_wrong_scope_fails(self, cache: AckCache) -> None:
        cache.grant("x")
        # Even though "inventive" is the only supported scope right now,
        # `check(scope="nonexistent")` must fail without throwing.
        assert cache.check("x", scope="nonexistent") is False

    def test_unsupported_scope_rejected_at_grant(self, cache: AckCache) -> None:
        with pytest.raises(ValueError):
            cache.grant("x", scope=["not-a-real-scope"])


class TestTTL:
    def test_expired_grant_fails_check(
        self, cache: AckCache, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cache.grant("x", ttl_days=7)
        future = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=10)
        assert cache.check("x", now=future) is False

    def test_not_yet_expired(self, cache: AckCache) -> None:
        cache.grant("x", ttl_days=7)
        mid = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=3)
        assert cache.check("x", now=mid) is True


class TestRevoke:
    def test_revoke_then_check_fails(self, cache: AckCache) -> None:
        cache.grant("x")
        assert cache.check("x") is True
        assert cache.revoke("x") is True
        assert cache.check("x") is False

    def test_revoke_nonexistent(self, cache: AckCache) -> None:
        assert cache.revoke("does-not-exist") is False


class TestList:
    def test_list_empty(self, cache: AckCache) -> None:
        assert cache.list_grants() == []

    def test_list_after_grants(self, cache: AckCache) -> None:
        cache.grant("a")
        cache.grant("b")
        names = {g.family for g in cache.list_grants()}
        assert names == {"a", "b"}


class TestTamper:
    def test_hmac_mismatch_fails_check(self, cache: AckCache) -> None:
        cache.grant("x")
        # Mutate the on-disk grant: change ttl to 999 to extend it without a
        # fresh HMAC. The check must reject because the signed HMAC covers
        # the ttl_days field.
        path = cache.root / f"{family_hash('x')}.json"
        body = json.loads(path.read_text())
        body["ttl_days"] = 999
        path.write_text(json.dumps(body))
        assert cache.check("x") is False

    def test_missing_key_fails_check(self, cache: AckCache) -> None:
        cache.grant("x")
        # Delete the HMAC key — existing grants can no longer be verified.
        # This is the expected behavior: losing the key invalidates grants.
        (cache.root / ".key").unlink()
        assert cache.check("x") is False


class TestSupportedScopes:
    def test_inventive_listed(self) -> None:
        assert "inventive" in SUPPORTED_SCOPES


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
