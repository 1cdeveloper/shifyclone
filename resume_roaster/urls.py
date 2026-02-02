from django.contrib import admin
from django.urls import path
from resume_roaster.bot.views import tma_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tma/", tma_view, name="tma"),
]

