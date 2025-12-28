
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('silk/', include('silk.urls', namespace='silk')),
    path('api/v1/users/', include('Users.urls.v1.users_urls')),
    path('api/v1/funds/', include('Funds.urls.v1.funds_urls')),
    path('api/v1/ads/', include('Ads.urls.v1.ads_urls')),
    path('api/v1/notifications/', include('Notification.urls.v1.notification_urls')),
    path('api/v1/lottery/', include('Lottery.urls.v1.lottery_urls')),
]
