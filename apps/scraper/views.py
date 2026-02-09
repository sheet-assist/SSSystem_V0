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
import threading    

User = get_user_model()


# =========================
# Dashboard
# =========================

class ScraperDashboardView(AdminRequiredMixin, ListView):
    """Display dashboard with all scrape jobs."""
    model = ScrapeJob
    template_name = "scraper/dashboard.html"
    context_object_name = "jobs"
    paginate_by = 20

    def get_queryset(self):
        return (
            ScrapeJob.objects
            .select_related("county", "county__state", "triggered_by")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["total_jobs"] = ScrapeJob.objects.count()
        ctx["pending_jobs"] = ScrapeJob.objects.filter(status="pending").count()
        ctx["running_jobs"] = ScrapeJob.objects.filter(status="running").count()
        ctx["completed_jobs"] = ScrapeJob.objects.filter(status="completed").count()
        ctx["failed_jobs"] = ScrapeJob.objects.filter(status="failed").count()

        ctx["total_prospects_created"] = (
            ScrapeJob.objects.aggregate(total=Sum("prospects_created"))["total"] or 0
        )

        return ctx


# =========================
# Trigger New Scrape
# =========================

class ScrapeTriggerView(AdminRequiredMixin, FormView):
    """Form to trigger a new scrape job."""
    template_name = "scraper/trigger.html"
    form_class = ScrapeTriggerForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Trigger New Scrape"
        return ctx

    def form_valid(self, form):
        county = form.cleaned_data["county"]
        prospect_type = form.cleaned_data["prospect_type"]
        target_date = form.cleaned_data["target_date"]

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

        return redirect("scraper:dashboard")


# =========================
# Copy Existing Scrape Job
# =========================

class ScrapeJobCopyView(AdminRequiredMixin, FormView):
    """Copy an existing scrape job and pre-fill the trigger form."""
    template_name = "scraper/trigger.html"
    form_class = ScrapeTriggerForm

    def get_initial(self):
        job = get_object_or_404(ScrapeJob, pk=self.kwargs["pk"])
        return {
            "state": job.county.state,
            "county": job.county,
            "prospect_type": job.job_type,
            "target_date": job.target_date,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Copy Scrape Job"
        ctx["copy_mode"] = True
        return ctx

    def form_valid(self, form):
        county = form.cleaned_data["county"]
        prospect_type = form.cleaned_data["prospect_type"]
        target_date = form.cleaned_data["target_date"]

        job = ScrapeJob.objects.create(
            county=county,
            job_type=prospect_type,
            target_date=target_date,
            triggered_by=self.request.user,
        )

        messages.success(
            self.request,
            f"Scrape job copied for {county.name} on {target_date}. Job ID: {job.pk}"
        )

        return redirect("scraper:dashboard")


# =========================
# Job Detail + Summary
# =========================

class ScrapeJobDetailView(AdminRequiredMixin, DetailView):
    """Display detailed view of a scrape job with logs."""
    model = ScrapeJob
    template_name = "scraper/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return (
            ScrapeJob.objects
            .select_related("county", "county__state", "triggered_by")
            .prefetch_related("logs")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        logs_qs = self.object.logs.order_by("-created_at")

        ctx["logs"] = logs_qs
        ctx["info_logs"] = logs_qs.filter(level="info").count()
        ctx["warning_logs"] = logs_qs.filter(level="warning").count()
        ctx["error_logs"] = logs_qs.filter(level="error").count()

        # Extract last error URL if present
        error_log = logs_qs.filter(level="error").first()
        error_url = None
        if error_log and "http" in error_log.message:
            import re
            match = re.search(r"(https?://\\S+)", error_log.message)
            if match:
                error_url = match.group(1)

        ctx["error_url"] = error_url
        return ctx


# =========================
# Job Logs (Paginated)
# =========================

class ScrapeLogListView(AdminRequiredMixin, ListView):
    """Display logs for a specific scrape job with filtering."""
    model = ScrapeLog
    template_name = "scraper/logs.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        job_id = self.kwargs.get("job_pk")
        self.job = get_object_or_404(ScrapeJob, pk=job_id)

        qs = ScrapeLog.objects.filter(job=self.job).order_by("-created_at")

        level_filter = self.request.GET.get("level")
        if level_filter:
            qs = qs.filter(level=level_filter)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job"] = self.job
        ctx["level_filter"] = self.request.GET.get("level", "")
        return ctx


# =========================
# Job Progress API (JSON)
# =========================

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


# =========================
# Run Job (Sync for now)
# =========================

class ScrapeJobRunView(AdminRequiredMixin, View):
    """Run a pending or failed scrape job immediately."""

    def post(self, request, pk):
        job = get_object_or_404(ScrapeJob, pk=pk, status__in=["pending", "failed"])

        try:
            job.status = "running"
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

            # 🔥 RUN IN BACKGROUND THREAD
            t = threading.Thread(target=run_scrape_job, args=(job.pk,))
            t.daemon = True
            t.start()

            messages.success(
                request,
                f"Scrape job #{job.pk} started in background."
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])

            messages.error(request, f"Scrape job #{job.pk} failed to start: {str(e)}")

        return redirect("scraper:job_detail", pk=job.pk)