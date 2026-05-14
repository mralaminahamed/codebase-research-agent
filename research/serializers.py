from __future__ import annotations

from rest_framework import serializers

from research.models import Finding, Repository, ResearchSession, ToolCall
from research.services.repo_service import RepoCloneError
from research.services.repo_service import validate_repo_url as _validate_repo_url


class RepositorySerializer(serializers.ModelSerializer):
    """Read serializer for :class:`~research.models.Repository`."""

    class Meta:
        model = Repository
        fields = ["id", "url", "name", "commit_sha"]


class CreateSessionSerializer(serializers.Serializer):
    """Input-only serializer for starting a new research session.

    Validates that ``repo_url`` is a well-formed public GitHub HTTPS URL
    before the session is created.
    """

    repo_url = serializers.URLField()
    question = serializers.CharField(min_length=10, max_length=2000)

    def validate_repo_url(self, value: str) -> str:
        """Check URL is a valid GitHub HTTPS URL.

        Args:
            value: The raw URL string from the request.

        Returns:
            The validated URL unchanged.

        Raises:
            serializers.ValidationError: If the URL fails GitHub URL validation.
        """
        try:
            _validate_repo_url(value)
        except RepoCloneError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class ToolCallSerializer(serializers.ModelSerializer):
    """Compact serializer for :class:`~research.models.ToolCall`.

    The ``result_preview`` field truncates large tool outputs to 500 characters
    to keep list responses lightweight.
    """

    result_preview = serializers.SerializerMethodField()

    def get_result_preview(self, obj: ToolCall) -> str:
        """Return the first 500 characters of the tool result.

        Args:
            obj: The :class:`~research.models.ToolCall` instance.

        Returns:
            Truncated result string with an ellipsis appended if truncated.
        """
        if len(obj.result) > 500:
            return obj.result[:500] + "…"
        return obj.result

    class Meta:
        model = ToolCall
        fields = [
            "sequence",
            "tool_name",
            "arguments",
            "result_preview",
            "duration_ms",
            "created_at",
        ]


class FindingSerializer(serializers.ModelSerializer):
    """Serializer for :class:`~research.models.Finding`."""

    class Meta:
        model = Finding
        fields = [
            "id",
            "file_path",
            "line_start",
            "line_end",
            "note",
            "confidence",
            "created_at",
        ]


class ResearchSessionListSerializer(serializers.ModelSerializer):
    """Compact serializer for listing research sessions.

    Exposes a ``question_preview`` (first 80 characters) instead of the
    full question text to keep list responses concise.
    """

    question_preview = serializers.SerializerMethodField()
    repository = RepositorySerializer(read_only=True)

    def get_question_preview(self, obj: ResearchSession) -> str:
        """Return the first 80 characters of the question.

        Args:
            obj: The :class:`~research.models.ResearchSession` instance.

        Returns:
            Truncated question string.
        """
        return obj.question[:80]

    class Meta:
        model = ResearchSession
        fields = [
            "id",
            "question_preview",
            "status",
            "started_at",
            "completed_at",
            "iterations",
            "input_tokens",
            "output_tokens",
            "repository",
        ]


class ResearchSessionDetailSerializer(ResearchSessionListSerializer):
    """Full serializer for a single research session.

    Extends :class:`ResearchSessionListSerializer` with the complete question,
    final answer, error text, and all nested tool calls and findings.
    """

    tool_calls = ToolCallSerializer(many=True, read_only=True)
    findings = FindingSerializer(many=True, read_only=True)

    class Meta(ResearchSessionListSerializer.Meta):
        fields = ResearchSessionListSerializer.Meta.fields + [
            "question",
            "final_answer",
            "error",
            "tool_calls",
            "findings",
        ]
