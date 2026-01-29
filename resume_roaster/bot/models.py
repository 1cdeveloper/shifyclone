from django.db import models


class ResumeProcessing(models.Model):
    """Модель для отслеживания обработки резюме"""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает обработки"),
        (STATUS_PROCESSING, "Обрабатывается"),
        (STATUS_COMPLETED, "Завершено"),
        (STATUS_FAILED, "Ошибка"),
    ]

    telegram_user_id = models.BigIntegerField(verbose_name="Telegram User ID")
    telegram_chat_id = models.BigIntegerField(verbose_name="Telegram Chat ID")
    telegram_message_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram Message ID")
    file_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Telegram File ID")
    resume_text = models.TextField(verbose_name="Текст резюме")
    roast_result = models.TextField(null=True, blank=True, verbose_name="Результат прожарки")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Статус")
    error_message = models.TextField(null=True, blank=True, verbose_name="Сообщение об ошибке")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Обработка резюме"
        verbose_name_plural = "Обработки резюме"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ResumeProcessing #{self.id} - {self.status}"

