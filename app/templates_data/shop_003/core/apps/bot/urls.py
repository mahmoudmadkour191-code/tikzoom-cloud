from django.urls import path, include

from core.apps.bot.views import index

urlpatterns = [
    path('', index),
    path('chaining/', include('smart_selects.urls'))
]
