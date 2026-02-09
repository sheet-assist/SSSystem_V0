from django.urls import path
from . import views

app_name = "scraper"

urlpatterns = [
    # ...existing urls...
    path("jobs/<int:pk>/copy/", views.ScrapeJobCopyView.as_view(), name="job_copy"),
]
