from django.contrib import admin

from research.models import Finding, Repository, ResearchSession, ToolCall


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    """Admin for Repository model."""

    list_display = ("id", "name", "url", "last_indexed_at")
    search_fields = ("url", "name")


def _truncated_question(obj: ResearchSession) -> str:
    return obj.question[:60]


_truncated_question.short_description = "question"  # type: ignore[attr-defined]


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    """Admin for ResearchSession model."""

    list_display = (
        "id",
        _truncated_question,
        "status",
        "repository",
        "iterations",
        "input_tokens",
        "started_at",
    )
    list_filter = ("status",)
    search_fields = ("question",)
    readonly_fields = ("id", "started_at", "completed_at")


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    """Admin for ToolCall model."""

    list_display = ("sequence", "tool_name", "duration_ms", "session", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    """Admin for Finding model."""

    list_display = ("file_path", "line_start", "line_end", "session", "created_at")
