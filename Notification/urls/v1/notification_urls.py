from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Notification.views.notification_views import UserNotificationViewSet

router = DefaultRouter()
router.register('notif', UserNotificationViewSet, basename='notifications')

urlpatterns = [
]
urlpatterns += router.urls