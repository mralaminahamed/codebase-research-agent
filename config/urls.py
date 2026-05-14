from django.contrib import admin
from django.urls import include, path

from research.views import IndexView

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("admin/", admin.site.urls),
    path("api/", include("research.urls", namespace="research")),
]
