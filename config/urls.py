from django.contrib import admin
from django.urls import include, path

from research.views import IndexView, ResearchUIView

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("research/", ResearchUIView.as_view(), name="research-ui"),
    path("admin/", admin.site.urls),
    path("api/", include("research.urls", namespace="research")),
]
