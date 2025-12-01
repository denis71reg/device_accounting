"""
URL configuration for ittest_buddy project.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.views import broadcast_message

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/broadcast/', broadcast_message, name='admin:broadcast_message'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

