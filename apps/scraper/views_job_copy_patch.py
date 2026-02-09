from django.shortcuts import redirect, get_object_or_404
from django.views.generic import FormView
from apps.accounts.mixins import AdminRequiredMixin
from .models import ScrapeJob
from .forms import ScrapeTriggerForm

class ScrapeJobCopyView(AdminRequiredMixin, FormView):
    template_name = "scraper/trigger.html"
    form_class = ScrapeTriggerForm

    def get_initial(self):
        job = get_object_or_404(ScrapeJob, pk=self.kwargs["pk"])
        return {
            "state": job.county.state.pk,
            "county": job.county.pk,
            "prospect_type": job.job_type,
            "target_date": job.target_date,
        }

    def form_valid(self, form):
        # Same as ScrapeTriggerView
        state = form.cleaned_data["state"]
        county = form.cleaned_data["county"]
        prospect_type = form.cleaned_data["prospect_type"]
        target_date = form.cleaned_data["target_date"]
        job = ScrapeJob.objects.create(
            county=county,
            job_type=prospect_type,
            target_date=target_date,
            triggered_by=self.request.user,
        )
        return redirect("scraper:dashboard")
