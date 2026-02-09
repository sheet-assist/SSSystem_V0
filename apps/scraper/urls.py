from django.urls import path

from . import views

app_name = "scraper"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.ScraperDashboardView.as_view(), name="dashboard"),
    
    # Trigger new scrape
    path("trigger/", views.ScrapeTriggerView.as_view(), name="trigger"),
    # Copy scrape job
    path("jobs/<int:pk>/copy/", views.ScrapeJobCopyView.as_view(), name="job_copy"),
    
    # Job detail and logs
    path("jobs/<int:pk>/", views.ScrapeJobDetailView.as_view(), name="job_detail"),
    path("jobs/<int:job_pk>/logs/", views.ScrapeLogListView.as_view(), name="logs"),
    
    # Progress API (JSON)
    path("jobs/<int:pk>/progress/", views.ScrapeJobProgressView.as_view(), name="job_progress"),
    
    # Run pending job
    path("jobs/<int:pk>/run/", views.ScrapeJobRunView.as_view(), name="job_run"),
]
