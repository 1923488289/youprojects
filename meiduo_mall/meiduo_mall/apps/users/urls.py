from django.conf.urls import url
from . import views

urlpatterns = [
    url('^register/$', views.RegisterView.as_view()),
    url('^usernames/(?P<username>[a-zA-Z0-9-_]{5,20})/count/$', views.UsernameCheckView.as_view()),
    url('^mobiles/(?P<mobile>1[345789]\d{9})/count/$', views.MobileCheckView.as_view()),
    url('^login/$', views.LoginView.as_view()),
    url('^logout/$', views.LogoutView.as_view()),
    url('^info/$', views.InfoView.as_view()),
    url('^emails/$', views.EmailView.as_view()),
    url('^emails/verification/$', views.EmailActiveView.as_view()),
    url('^addresses/$', views.AddressView.as_view()),
    url('^addresses/create/$', views.AddressCreateView.as_view()),
    url('^addresses/(?P<address_id>\d+)/$', views.AddressUpdateView.as_view()),
    url('^addresses/(?P<address_id>\d+)/default/$', views.AddressDefaultView.as_view()),
    url('^addresses/(?P<address_id>\d+)/title/$', views.AddressTitleView.as_view()),
    url('^password/$', views.PasswordView.as_view()),
]
