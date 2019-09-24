from django.conf.urls import url
from . import views

urlpatterns = [
    url('^orders/settlement/$', views.PlaceOrderView.as_view()),
    url('^orders/commit/$', views.CommitView.as_view()),
    url('^orders/success/$', views.SuccessView.as_view()),
    url('^orders/info/(?P<page_num>\d+)/$', views.OrderListView.as_view()),
    url('^orders/comment/$', views.OrderCommentView.as_view()),
    url('^comment/(?P<sku_id>\d+)/$', views.CommentListView.as_view()),
]
