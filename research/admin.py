from django.contrib import admin
from django.utils.html import format_html

from research.models import Finding, Repository, ResearchSession, ToolCall


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    """Admin for Repository model."""

    list_display = ("id", "name", "url", "commit_sha_short", "last_indexed_at", "created_at")
    search_fields = ("url", "name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def commit_sha_short(self, obj: Repository) -> str:
        return obj.commit_sha[:8] if obj.commit_sha else "—"

    commit_sha_short.short_description = "commit"  # type: ignore[attr-defined]


def _truncated_question(obj: ResearchSession) -> str:
    return obj.question[:70]


_truncated_question.short_description = "question"  # type: ignore[attr-defined]


def _token_total(obj: ResearchSession) -> int:
    return obj.input_tokens + obj.output_tokens


_token_total.short_description = "total tokens"  # type: ignore[attr-defined]


def _status_badge(obj: ResearchSession) -> str:
    colours = {
        "PENDING": "#6c757d",
        "RUNNING": "#0d6efd",
        "COMPLETE": "#198754",
        "FAILED": "#dc3545",
    }
    colour = colours.get(obj.status, "#6c757d")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:600">{}</span>',
        colour,
        obj.status,
    )


_status_badge.short_description = "status"  # type: ignore[attr-defined]
_status_badge.allow_tags = True  # type: ignore[attr-defined]


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    """Admin for ResearchSession model."""

    list_display = (
        "id",
        _truncated_question,
        _status_badge,
        "repository",
        "iterations",
        _token_total,
        "started_at",
    )
    list_filter = ("status", "repository")
    search_fields = ("question", "final_answer")
    readonly_fields = ("id", "started_at", "completed_at", "input_tokens", "output_tokens", "iterations")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)

    fieldsets = (
        (None, {
            "fields": ("id", "repository", "question", "status"),
        }),
        ("Answer", {
            "fields": ("final_answer", "error"),
            "classes": ("collapse",),
        }),
        ("Metrics", {
            "fields": ("iterations", "input_tokens", "output_tokens"),
        }),
        ("Timestamps", {
            "fields": ("started_at", "completed_at"),
        }),
    )


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    """Admin for ToolCall model."""

    list_display = ("sequence", "tool_name", "duration_ms", "session", "created_at")
    list_filter = ("tool_name",)
    search_fields = ("tool_name", "session__question")
    readonly_fields = ("created_at",)
    ordering = ("session", "sequence")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    """Admin for Finding model."""

    list_display = ("file_path", "line_start", "line_end", "confidence", "session", "created_at")
    list_filter = ("session__status",)
    search_fields = ("file_path", "note", "session__question")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
