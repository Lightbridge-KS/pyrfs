"""User and group lookups — POSIX via ``pwd``/``grp``; empty on Windows."""

from __future__ import annotations

__all__ = ["group_ids", "user_ids"]


def user_ids() -> list[dict[str, object]]:
    """All known users as rows of ``{"user_id", "user_name"}``.

    Returns an empty list on platforms without ``pwd`` (Windows).
    """
    try:
        import pwd
    except ImportError:
        return []
    return [{"user_id": e.pw_uid, "user_name": e.pw_name} for e in pwd.getpwall()]


def group_ids() -> list[dict[str, object]]:
    """All known groups as rows of ``{"group_id", "group_name"}``.

    Returns an empty list on platforms without ``grp`` (Windows).
    """
    try:
        import grp
    except ImportError:
        return []
    return [{"group_id": e.gr_gid, "group_name": e.gr_name} for e in grp.getgrall()]
