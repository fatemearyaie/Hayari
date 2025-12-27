from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from Notification.models.notification_models import UserNotification
from Notification.serializers.notification_serializers import UserNotificationSerializer


class UserNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read']

    def get_queryset(self):
        return UserNotification.objects.select_related('user').filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated_count = UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'all read count': updated_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = get_object_or_404(UserNotification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response('one notification read',status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread count': count}, status=status.HTTP_200_OK)

