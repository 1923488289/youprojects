from django.conf.urls import url
from . import views

urlpatterns = [
    url('^payment/(?P<order_id>\d+)/$', views.AlipayUrlView.as_view()),
    url('^payment/status/$', views.AlipayVerifyView.as_view()),
]
