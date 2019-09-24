from django.conf.urls import url
from . import views

urlpatterns = [
    url('^image_codes/(?P<uuid>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/$',
        views.ImagecodeView.as_view()),
    url('^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SmscodeView.as_view()),
]
