from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Notification.views.notification_views import UserNotificationViewSet, RegisterFCMTokenView

router = DefaultRouter()
router.register('notif', UserNotificationViewSet, basename='notifications')


urlpatterns = [
    path("fcm-token/", RegisterFCMTokenView.as_view(), name="register-fcm-token"),
]
urlpatterns += router.urls