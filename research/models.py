import uuid

from django.db import models


class Repository(models.Model):
    """A GitHub repository that has been or will be researched.

    Attributes:
        url: Canonical GitHub URL, unique per repository.
        name: Short name extracted from the URL path (e.g. ``owner/repo``).
        default_branch: Branch to clone, defaults to ``main``.
        last_indexed_at: Timestamp of the most recent successful clone/update.
        commit_sha: HEAD commit SHA after the last clone.
        created_at: Row creation timestamp.
    """

    url = models.URLField(unique=True, db_index=True)
    name = models.CharField(max_length=200)
    default_branch = models.CharField(max_length=100, default="main")
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    commit_sha = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "repositories"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_url(cls, url: str) -> "Repository":
        """Get or create a Repository from its GitHub URL.

        Extracts the repo name from the final two path segments
        (``owner/repo``) so the name is human-readable.

        Args:
            url: Full GitHub repository URL, e.g.
                ``https://github.com/django/django``.

        Returns:
            Existing or newly created :class:`Repository` instance.
        """
        url = url.rstrip("/")
        parts = url.rstrip(".git").rstrip("/").split("/")
        name = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
        repo, _ = cls.objects.get_or_create(url=url, defaults={"name": name})
        return repo


class ResearchSession(models.Model):
    """A single research run against a repository.

    Attributes:
        id: UUID primary key.
        repository: The repository being researched.
        question: Natural-language question submitted by the user.
        final_answer: LLM-generated answer written when status reaches COMPLETE.
        status: Lifecycle state of this session.
        iterations: Number of agent loop iterations consumed.
        input_tokens: Cumulative input tokens across all LLM calls.
        output_tokens: Cumulative output tokens across all LLM calls.
        error: Failure message when status is FAILED.
        started_at: Row creation timestamp.
        completed_at: Timestamp set when the agent loop exits.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETE = "COMPLETE", "Complete"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="sessions"
    )
    question = models.TextField()
    final_answer = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    iterations = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["repository", "-started_at"])]

    def __str__(self) -> str:
        return f"{self.repository.name} — {self.question[:60]}"


class ToolCall(models.Model):
    """A single tool invocation recorded during an agent loop iteration.

    Attributes:
        session: The research session this call belongs to.
        sequence: 0-based ordering index within the session.
        tool_name: Name of the dispatched tool function.
        arguments: Parsed JSON arguments passed to the tool.
        result: String output returned by the tool.
        duration_ms: Wall-clock time the tool execution took.
        created_at: Row creation timestamp.
    """

    session = models.ForeignKey(
        ResearchSession, on_delete=models.CASCADE, related_name="tool_calls"
    )
    sequence = models.PositiveIntegerField()
    tool_name = models.CharField(max_length=100)
    arguments = models.JSONField(default=dict)
    result = models.TextField()
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("session", "sequence")]
        ordering = ["session", "sequence"]

    def __str__(self) -> str:
        return f"[{self.sequence}] {self.tool_name}"


class Finding(models.Model):
    """A code location or fact surfaced during a research session.

    Attributes:
        session: The session that produced this finding.
        file_path: Repo-relative file path where the finding was located.
        line_start: First line of the relevant code span (1-based).
        line_end: Last line of the relevant code span (inclusive).
        note: Human-readable description of what was found.
        confidence: Optional 0–1 confidence score assigned by the agent.
        created_at: Row creation timestamp.
    """

    session = models.ForeignKey(
        ResearchSession, on_delete=models.CASCADE, related_name="findings"
    )
    file_path = models.CharField(max_length=500, db_index=True)
    line_start = models.PositiveIntegerField(null=True, blank=True)
    line_end = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField()
    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["session", "file_path"])]

    def __str__(self) -> str:
        return f"{self.file_path} ({self.session_id})"
