"""Prompt template rendering.

Uses Jinja2 if available (it's already in Django's deps); else a simple
str.format-with-dotted-vars fallback. Variables are expected to live in
`AIPromptVersion.variables` (the schema/defaults) and are merged with
runtime variables from the gateway request.
"""
from __future__ import annotations

from typing import Any

try:  # Jinja2 ships with most Django installs
    from jinja2 import Environment, StrictUndefined, select_autoescape

    _ENV: Any = Environment(
        autoescape=select_autoescape(default=False),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    _USE_JINJA = True
except Exception:  # pragma: no cover
    _ENV = None
    _USE_JINJA = False


def render_template(template: str, variables: dict[str, Any]) -> str:
    if not template:
        return ""
    if _USE_JINJA:
        try:
            return _ENV.from_string(template).render(**variables)
        except Exception as exc:
            raise ValueError(f"Prompt render error: {exc}") from exc
    # Fallback: convert Jinja `{{var}}` → Python `{var}` then use str.format.
    import re as _re
    converted = _re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", r"{\1}", template)
    try:
        return converted.format(**variables)
    except Exception as exc:
        raise ValueError(f"Prompt render error: {exc}") from exc


def render_prompt_version(prompt_version, variables: dict[str, Any]) -> tuple[str, str]:
    """Return ``(system_prompt, user_prompt)`` for a given AIPromptVersion row.

    Defaults from `prompt_version.variables` (a dict) are merged BEHIND the
    caller-supplied variables so callers can override.
    """
    defaults = prompt_version.variables or {}
    merged = {**defaults, **(variables or {})}
    system = render_template(prompt_version.system_prompt or "", merged)
    user = render_template(prompt_version.user_template or "", merged)
    return system, user
