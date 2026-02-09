from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import FormView, ListView, DetailView, View
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse

from apps.accounts.mixins import AdminRequiredMixin
from apps.locations.models import County

from .forms import ScrapeTriggerForm
from .models import ScrapeJob, ScrapeLog
from .engine import run_scrape_job

User = get_user_model()


class ScraperDashboardView(AdminRequiredMixin, ListView):
    """Display dashboard with all scrape jobs."""
    model = ScrapeJob
    template_name = "scraper/dashboard.html"
    context_object_name = "jobs"
    paginate_by = 20

    def get_queryset(self):
        return ScrapeJob.objects.select_related(
            "county", "county__state", "triggered_by"
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Statistics
        ctx["total_jobs"] = ScrapeJob.objects.count()
        ctx["pending_jobs"] = ScrapeJob.objects.filter(status="pending").count()
        ctx["running_jobs"] = ScrapeJob.objects.filter(status="running").count()
        ctx["completed_jobs"] = ScrapeJob.objects.filter(status="completed").count()
        ctx["failed_jobs"] = ScrapeJob.objects.filter(status="failed").count()
        
        # Total prospects from jobs
        ctx["total_prospects_created"] = ScrapeJob.objects.aggregate(
            total=Sum("prospects_created")
        )["total"] or 0
        
        return ctx


class ScrapeTriggerView(AdminRequiredMixin, FormView):
    """Form to trigger a new scrape job."""
    template_name = "scraper/trigger.html"
    form_class = ScrapeTriggerForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Trigger New Scrape"
        return ctx

    def form_valid(self, form):
        state = form.cleaned_data["state"]
        county = form.cleaned_data["county"]
        prospect_type = form.cleaned_data["prospect_type"]
        target_date = form.cleaned_data["target_date"]

        # Create scrape job
        job = ScrapeJob.objects.create(
            county=county,
            job_type=prospect_type,
            target_date=target_date,
            triggered_by=self.request.user,
        )

        messages.success(
            self.request,
            f"Scrape job created for {county.name} on {target_date}. Job ID: {job.pk}"
        )

        # For now, redirect to dashboard
        # In production, you might want to trigger async task here
        return redirect("scraper:dashboard")


class ScrapeJobDetailView(AdminRequiredMixin, DetailView):
    """Display detailed view of a scrape job with logs."""
    model = ScrapeJob
    template_name = "scraper/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return ScrapeJob.objects.select_related(
            "county", "county__state", "triggered_by"
        ).prefetch_related("logs")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = self.object.logs.order_by("-created_at").all()
        ctx["info_logs"] = self.object.logs.filter(level="info").count()
        ctx["warning_logs"] = self.object.logs.filter(level="warning").count()
        ctx["error_logs"] = self.object.logs.filter(level="error").count()
        return ctx


class ScrapeLogListView(AdminRequiredMixin, ListView):
    """Display logs for a specific scrape job with filtering."""
    model = ScrapeLog
    template_name = "scraper/logs.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        job_id = self.kwargs.get("job_pk")
        self.job = get_object_or_404(ScrapeJob, pk=job_id)
        return ScrapeLog.objects.filter(job=self.job).order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job"] = self.job
        ctx["level_filter"] = self.request.GET.get("level", "")
        if ctx["level_filter"]:
            ctx["object_list"] = ctx["object_list"].filter(level=ctx["level_filter"])
        return ctx


class ScrapeJobProgressView(AdminRequiredMixin, DetailView):
    """API endpoint to get real-time progress data for a scrape job."""
    model = ScrapeJob
    context_object_name = "job"

    def get_queryset(self):
        return ScrapeJob.objects.select_related("county", "county__state")

    def render_to_response(self, context, **response_kwargs):
        job = context["job"]
        return JsonResponse({
            "id": job.pk,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "progress_message": job.progress_message,
            "prospects_processed": job.prospects_processed,
            "total_prospects_found": job.total_prospects_found,
            "prospects_created": job.prospects_created,
            "prospects_updated": job.prospects_updated,
            "prospects_qualified": job.prospects_qualified,
            "prospects_disqualified": job.prospects_disqualified,
            "error_message": job.error_message,
        })


class ScrapeJobRunView(AdminRequiredMixin, View):
    """Run a pending scrape job immediately."""

    def post(self, request, pk):
        job = get_object_or_404(ScrapeJob, pk=pk, status='pending')
        
        try:
            # Run the scrape job
            run_scrape_job(job)
            messages.success(request, f"Scrape job #{job.pk} completed successfully!")
        except Exception as e:
            messages.error(request, f"Scrape job #{job.pk} failed: {str(e)}")
        
        # Redirect back to job detail or dashboard
        return redirect('scraper:job_detail', pk=job.pk)
