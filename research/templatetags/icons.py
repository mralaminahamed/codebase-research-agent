"""Inline Lucide SVG icon template tag.

Usage::

    {% load icons %}
    {% icon "package" cls="w-6 h-6 text-amber" %}
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Lucide icon paths — viewBox="0 0 24 24", stroke="currentColor", fill="none"
_PATHS: dict[str, str] = {
    "package": (
        '<path d="M16.5 9.4 7.55 4.24"/>'
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 2 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '<polyline points="3.29 7 12 12 20.71 7"/>'
        '<line x1="12" x2="12" y1="22" y2="12"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5V19A9 3 0 0 0 21 19V5"/>'
        '<path d="M3 12A9 3 0 0 0 21 12"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="8"/>'
        '<path d="m21 21-4.3-4.3"/>'
    ),
    "circle-check": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "microscope": (
        '<path d="M6 18h8"/>'
        '<path d="M3 22h18"/>'
        '<path d="M14 22a7 7 0 1 0 0-14h-1"/>'
        '<path d="M9 14h2"/>'
        '<path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"/>'
        '<path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>'
    ),
    "play": (
        '<polygon points="6 3 20 12 6 21 6 3"/>'
    ),
    "chevron-right": (
        '<path d="m9 18 6-6-6-6"/>'
    ),
    "terminal": (
        '<polyline points="4 17 10 11 4 5"/>'
        '<line x1="12" x2="20" y1="19" y2="19"/>'
    ),
    "loader": (
        '<line x1="12" x2="12" y1="2" y2="6"/>'
        '<line x1="12" x2="12" y1="18" y2="22"/>'
        '<line x1="4.93" x2="7.76" y1="4.93" y2="7.76"/>'
        '<line x1="16.24" x2="19.07" y1="16.24" y2="19.07"/>'
        '<line x1="2" x2="6" y1="12" y2="12"/>'
        '<line x1="18" x2="22" y1="12" y2="12"/>'
        '<line x1="4.93" x2="7.76" y1="19.07" y2="16.24"/>'
        '<line x1="16.24" x2="19.07" y1="7.76" y2="4.93"/>'
    ),
    "book-open": (
        '<path d="M12 7v14"/>'
        '<path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>'
    ),
    "git-branch": (
        '<line x1="6" x2="6" y1="3" y2="15"/>'
        '<circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<path d="M18 9a9 9 0 0 1-9 9"/>'
    ),
    "cpu": (
        '<rect width="16" height="16" x="4" y="4" rx="2"/>'
        '<rect width="6" height="6" x="9" y="9" rx="1"/>'
        '<path d="M15 2v2"/><path d="M15 20v2"/>'
        '<path d="M2 15h2"/><path d="M2 9h2"/>'
        '<path d="M20 15h2"/><path d="M20 9h2"/>'
        '<path d="M9 2v2"/><path d="M9 20v2"/>'
    ),
    "flask-conical": (
        '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 18.29A1 1 0 0 0 5.596 20h12.808a1 1 0 0 0 .877-1.71l-5.069-7.867A2 2 0 0 1 14 9.527V2"/>'
        '<path d="M8.5 2h7"/>'
        '<path d="M7 16h10"/>'
    ),
}


@register.simple_tag
def icon(name: str, cls: str = "w-5 h-5") -> str:
    """Render a Lucide icon as an inline SVG.

    Args:
        name: Icon slug (e.g. ``"package"``, ``"search"``).
        cls: CSS classes applied to the ``<svg>`` element.

    Returns:
        Safe HTML string containing the SVG element.
    """
    paths = _PATHS.get(name, "")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" class="{cls}">'
        f"{paths}</svg>"
    )
    return mark_safe(svg)
