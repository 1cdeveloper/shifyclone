from django.contrib import admin

from .models import ResumeProcessing


@admin.register(ResumeProcessing)
class ResumeProcessingAdmin(admin.ModelAdmin):
    list_display = ["id", "telegram_user_id", "status", "created_at", "updated_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["telegram_user_id", "resume_text"]
    readonly_fields = ["created_at", "updated_at"]

