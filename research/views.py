from __future__ import annotations

from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from research.models import Repository, ResearchSession
from research.serializers import (
    CreateSessionSerializer,
    ResearchSessionDetailSerializer,
    ResearchSessionListSerializer,
)
from research.services import agent
from research.services.repo_service import RepoCloneError


class IndexView(TemplateView):
    """Landing page at /."""

    template_name = "research/index.html"


class StartSessionView(APIView):
    """Start a new research session against a public GitHub repository.

    Validates the request, creates the session row, runs the agent loop
    synchronously, and returns the completed session detail.

    ``POST /api/sessions/``
    """

    def post(self, request: Request) -> Response:
        """Accept a repository URL and question, run the agent, return the result.

        Args:
            request: DRF request with ``repo_url`` and ``question`` in the body.

        Returns:
            201 with :class:`~research.serializers.ResearchSessionDetailSerializer`
            data on success, or 400 with ``{"error": "..."}`` if the URL is
            invalid or the clone fails.
        """
        serializer = CreateSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        repo_url: str = serializer.validated_data["repo_url"]
        question: str = serializer.validated_data["question"]

        repo = Repository.from_url(repo_url)
        session = ResearchSession.objects.create(repository=repo, question=question)

        try:
            agent.run(session)
        except RepoCloneError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ResearchSessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class SessionDetailView(RetrieveAPIView):
    """Retrieve a single research session by UUID.

    ``GET /api/sessions/<uuid:pk>/``
    """

    queryset = ResearchSession.objects.select_related("repository").prefetch_related(
        "tool_calls", "findings"
    )
    serializer_class = ResearchSessionDetailSerializer


class RepositorySessionsView(ListAPIView):
    """List all research sessions for a given repository, newest first.

    Pagination is applied automatically via ``REST_FRAMEWORK["PAGE_SIZE"]``.

    ``GET /api/repositories/<pk>/sessions/``
    """

    serializer_class = ResearchSessionListSerializer

    def get_queryset(self):
        """Filter sessions to the repository identified by ``pk``.

        Returns:
            Queryset of :class:`~research.models.ResearchSession` rows ordered
            by ``-started_at``.
        """
        return (
            ResearchSession.objects.filter(repository_id=self.kwargs["pk"])
            .select_related("repository")
            .order_by("-started_at")
        )
