"""Autonomy ack-cache — user consent for `creativity=inventive` without a
synchronous human in the loop.

v0.13.x Fix 3 rationale — the `architect-mode` skill never allows the agent
to activate `inventive` unilaterally (that would be moving-target-loss).
In synchronous sessions the user types an ack word or provides an inline
flag. Autonomous runs (`/loop`, cron-scheduled remote agents, nightly
pipelines) have no human present, so `inventive` degrades silently to
`standard`. This module lets a user **pre-grant** consent scoped to a task
family, signed with an HMAC derived from a user-local key, so the
architect-mode skill can check the cache during autonomous runs instead
of downgrading.

File layout:
    ~/.claude/ldd-acks/
        .key                 HMAC key, 64 random bytes, mode 0600
        <family_hash>.json   per-grant file, one object per family

Grant schema:
    {
      "family":      "<human-readable name>",       # e.g. "billing-schema-changes"
      "family_hash": "<sha256 hex>",                # sha256(family), 64 hex
      "scope":       ["inventive"],                  # future: may add other scopes
      "granted_at":  "2026-04-22T17:30:00Z",
      "ttl_days":    30,
      "hmac":        "<hex>",                        # HMAC-SHA256 of the signed body
    }

Check contract:
    - family match — caller passes either the human name (hashed on lookup)
      or the raw hash. Miss → invalid.
    - scope contains the requested scope.
    - granted_at + ttl_days >= now → valid.
    - HMAC matches — tamper-proofs the on-disk file.
    - Revoked grants are removed; absence of file == invalid.

The key is auto-generated on first grant. Losing it invalidates all grants
(they cannot HMAC-verify). That is the intended failure mode — short-TTL
grants make re-granting cheap and safer than re-using a leaked key.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


SUPPORTED_SCOPES = ("inventive",)
DEFAULT_TTL_DAYS = 30


def _default_root() -> Path:
    """Ack-cache root — honors ``$LDD_ACK_ROOT`` for tests, else ``~/.claude/ldd-acks/``."""
    override = os.environ.get("LDD_ACK_ROOT")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / "ldd-acks"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def family_hash(family: str) -> str:
    """Deterministic family hash — sha256 of the UTF-8-encoded name."""
    return hashlib.sha256(family.encode("utf-8")).hexdigest()


def _key_path(root: Path) -> Path:
    return root / ".key"


def _load_or_create_key(root: Path) -> bytes:
    """Read HMAC key from ``root/.key``; create one atomically if absent.

    Chmod to 0600 (owner-only) on creation. The rest of LDD never needs to
    read the key — only grant / check paths use it.
    """
    key_path = _key_path(root)
    if key_path.exists():
        return key_path.read_bytes()
    root.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(64)
    # Write exclusively to avoid a race with a parallel first-grant.
    try:
        fd = os.open(str(key_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    except FileExistsError:
        return key_path.read_bytes()
    return key


def _sign(key: bytes, body: dict) -> str:
    # Signed body excludes the hmac field itself.
    canonical = json.dumps(
        {k: v for k, v in body.items() if k != "hmac"},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


@dataclass
class Grant:
    family: str
    family_hash: str
    scope: List[str] = field(default_factory=lambda: ["inventive"])
    granted_at: str = field(default_factory=_now_iso)
    ttl_days: int = DEFAULT_TTL_DAYS
    hmac: str = ""

    def to_body(self) -> dict:
        return {
            "family": self.family,
            "family_hash": self.family_hash,
            "scope": list(self.scope),
            "granted_at": self.granted_at,
            "ttl_days": int(self.ttl_days),
            "hmac": self.hmac,
        }

    @classmethod
    def from_body(cls, body: dict) -> "Grant":
        return cls(
            family=body["family"],
            family_hash=body["family_hash"],
            scope=list(body.get("scope", ["inventive"])),
            granted_at=body["granted_at"],
            ttl_days=int(body.get("ttl_days", DEFAULT_TTL_DAYS)),
            hmac=body.get("hmac", ""),
        )

    def is_expired(self, now: Optional[_dt.datetime] = None) -> bool:
        if now is None:
            now = _dt.datetime.now(_dt.timezone.utc)
        try:
            granted = _dt.datetime.fromisoformat(self.granted_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        return now > granted + _dt.timedelta(days=self.ttl_days)


class AckCache:
    """Grant/revoke/list/check over the on-disk cache."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else _default_root()

    def _file_for(self, fhash: str) -> Path:
        return self.root / f"{fhash}.json"

    def grant(
        self,
        family: str,
        scope: Optional[List[str]] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> Grant:
        scope = list(scope) if scope is not None else ["inventive"]
        for s in scope:
            if s not in SUPPORTED_SCOPES:
                raise ValueError(f"unsupported scope: {s!r}")
        fhash = family_hash(family)
        key = _load_or_create_key(self.root)
        body = Grant(
            family=family,
            family_hash=fhash,
            scope=scope,
            granted_at=_now_iso(),
            ttl_days=ttl_days,
            hmac="",
        ).to_body()
        body["hmac"] = _sign(key, body)
        # Persist atomically via a tempfile swap.
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._file_for(fhash)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        tmp.replace(path)
        return Grant.from_body(body)

    def revoke(self, family: str) -> bool:
        fhash = family_hash(family)
        path = self._file_for(fhash)
        if path.exists():
            path.unlink()
            return True
        return False

    def _read(self, fhash: str) -> Optional[Grant]:
        path = self._file_for(fhash)
        if not path.exists():
            return None
        try:
            body = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        return Grant.from_body(body)

    def list_grants(self) -> List[Grant]:
        if not self.root.exists():
            return []
        out: List[Grant] = []
        for p in sorted(self.root.glob("*.json")):
            try:
                body = json.loads(p.read_text())
                out.append(Grant.from_body(body))
            except (json.JSONDecodeError, OSError, KeyError):
                continue
        return out

    def check(
        self,
        family: str,
        scope: str = "inventive",
        now: Optional[_dt.datetime] = None,
    ) -> bool:
        """Return True iff a non-tampered, non-expired grant for family+scope exists."""
        fhash = family_hash(family)
        grant = self._read(fhash)
        if grant is None:
            return False
        if scope not in grant.scope:
            return False
        if grant.is_expired(now=now):
            return False
        # HMAC verify — the signed body EXCLUDES the hmac field.
        if not _key_path(self.root).exists():
            return False
        key = _key_path(self.root).read_bytes()
        expected = _sign(key, grant.to_body())
        return hmac.compare_digest(expected, grant.hmac)
