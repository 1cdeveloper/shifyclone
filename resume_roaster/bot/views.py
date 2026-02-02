from django.shortcuts import render

def tma_view(request):
    """
    Представление для отображения Telegram Mini App.
    """
    return render(request, "bot/tma.html")
