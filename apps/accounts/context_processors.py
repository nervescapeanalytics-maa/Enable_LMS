"""
Context processors for the accounts app.

`nav_permissions` exposes two values into every template render:

    nav_perms     -- a frozenset of allowed nav codes for the current user
    nav_sections  -- a dict {section_key: bool} indicating whether any
                     item in that sidebar section is visible

Templates can then do::

    {% if 'nav.master.batches' in nav_perms %} ... {% endif %}
    {% if nav_sections.master %} <div class="sb-section"> ... </div> {% endif %}

Fallback rules (kept permissive so we never lock out legitimate admins
before the seed command has been run):

    * Anonymous users                       -> empty set
    * Admin with no staff_role assigned     -> ALL codes (legacy compat)
    * Admin whose staff_role level is
      SUPER_ADMIN                           -> ALL codes
    * Anyone else                           -> exactly the codes seeded
                                               in NavMenuPermission rows

The full catalog of valid codes lives in
``accounts.management.commands.seed_staff_nav_permissions.NAV_CATALOG``;
this module imports it lazily so app loading order stays safe.
"""
from __future__ import annotations

from typing import FrozenSet


_ALL_CODES_CACHE: FrozenSet[str] | None = None


def _all_codes() -> FrozenSet[str]:
    global _ALL_CODES_CACHE
    if _ALL_CODES_CACHE is None:
        # Local import to avoid circulars at app-loading time.
        from accounts.management.commands.seed_staff_nav_permissions import (
            NAV_CATALOG,
        )
        codes = set()
        for section in NAV_CATALOG.values():
            codes.update(section['items'].keys())
        _ALL_CODES_CACHE = frozenset(codes)
    return _ALL_CODES_CACHE


def _section_map(allowed: FrozenSet[str]) -> dict:
    """Return {section_key: bool} = any item in that section visible."""
    from accounts.management.commands.seed_staff_nav_permissions import (
        NAV_CATALOG,
    )
    out = {}
    for section_key, section in NAV_CATALOG.items():
        out[section_key] = any(code in allowed for code in section['items'])
    return out


def nav_permissions(request):
    user = getattr(request, 'user', None)
    if user is None:
        return {'nav_perms': frozenset(), 'nav_sections': {}}

    # Django's AnonymousUser has is_authenticated == False; our custom
    # Admin / BaseUser model is a plain models.Model and exposes neither
    # `is_authenticated` nor an explicit anon flag. Treat the user as
    # authenticated if they have a primary key AND are not the
    # AnonymousUser sentinel.
    is_authed = getattr(user, 'is_authenticated', None)
    if is_authed is None:
        is_authed = bool(getattr(user, 'pk', None))
    if not is_authed:
        return {'nav_perms': frozenset(), 'nav_sections': {}}

    # Custom Admin model is our staff-portal user. Other user types
    # (Student, Teacher, Parent) never see the staff sidebar so they
    # safely get an empty set.
    staff_role = getattr(user, 'staff_role', None)

    # Legacy / super-admin / unconfigured -> show everything.
    if staff_role is None:
        allowed = _all_codes()
    elif getattr(staff_role, 'level', '') == 'SUPER_ADMIN':
        allowed = _all_codes()
    else:
        try:
            codes = staff_role.nav_permissions.values_list('code', flat=True)
            allowed = frozenset(codes)
        except Exception:
            # Defensive: if the table doesn't exist yet (pre-migrate),
            # don't crash the staff dashboard.
            allowed = _all_codes()

    return {
        'nav_perms': allowed,
        'nav_sections': _section_map(allowed),
    }
