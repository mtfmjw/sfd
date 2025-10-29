from django.urls import path

from sfd.views.index import IndexView
from sfd.views.municipality import get_municipalities_by_prefecture
from sfd.views.postcode import PostcodeSearchView

app_name = "sfd"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("change_prefecture/", get_municipalities_by_prefecture, name="change_prefecture"),
    path("search_postcode/", PostcodeSearchView.as_view(), name="search_postcode"),
]
