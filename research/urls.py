from django.urls import path

from research.views import IndexView, RepositorySessionsView, SessionDetailView, StartSessionView

app_name = "research"

urlpatterns = [
    path("sessions/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<uuid:pk>/", SessionDetailView.as_view(), name="session-detail"),
    path(
        "repositories/<int:pk>/sessions/",
        RepositorySessionsView.as_view(),
        name="repository-sessions",
    ),
]
