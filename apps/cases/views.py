from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView
from django_filters.views import FilterView

from apps.accounts.mixins import AdminRequiredMixin, CasesAccessMixin, ProspectsAccessMixin
from apps.locations.models import County, State
from apps.prospects.models import Prospect

from .filters import CaseFilter
from .forms import CaseNoteForm, CaseFollowUpForm, CaseStatusForm, ConvertProspectForm
from .models import Case, CaseNote, CaseFollowUp, log_case_action

User = get_user_model()


# --- Case List & Detail Views ---

class CaseListView(CasesAccessMixin, FilterView):
    """List all cases with filtering by type, status, assigned_to."""
    model = Case
    template_name = "cases/list.html"
    filterset_class = CaseFilter
    paginate_by = 25

    def get_queryset(self):
        return Case.objects.select_related(
            "prospect", "prospect__county", "prospect__county__state", "assigned_to"
        ).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Cases"
        return ctx


class CaseDetailView(CasesAccessMixin, DetailView):
    """Display detailed view of a single case with all related notes and follow-ups."""
    model = Case
    template_name = "cases/detail.html"

    def get_queryset(self):
        return Case.objects.select_related(
            "prospect", "prospect__county", "prospect__county__state", "assigned_to"
        ).prefetch_related(
            "notes__author",
            "followups__assigned_to",
            "action_logs__user"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notes"] = self.object.notes.select_related("author").all()
        ctx["followups"] = self.object.followups.select_related("assigned_to").all()
        ctx["logs"] = self.object.action_logs.select_related("user").all()
        return ctx


# --- Case Notes ---

class CaseNoteCreateView(CasesAccessMixin, CreateView):
    """Create a new note for a case."""
    model = CaseNote
    form_class = CaseNoteForm
    template_name = "cases/note_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.case = get_object_or_404(Case, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["case"] = self.case
        return ctx

    def form_valid(self, form):
        form.instance.case = self.case
        form.instance.author = self.request.user
        resp = super().form_valid(form)
        log_case_action(self.case, self.request.user, "note_added", "Note added")
        messages.success(self.request, "Note added.")
        return resp

    def get_success_url(self):
        return reverse("cases:detail", kwargs={"pk": self.case.pk})


# --- Case Follow-ups ---

class CaseFollowUpCreateView(CasesAccessMixin, CreateView):
    """Create a new follow-up reminder for a case."""
    model = CaseFollowUp
    form_class = CaseFollowUpForm
    template_name = "cases/followup_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.case = get_object_or_404(Case, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["case"] = self.case
        return ctx

    def form_valid(self, form):
        form.instance.case = self.case
        resp = super().form_valid(form)
        log_case_action(
            self.case, self.request.user, "followup_added",
            f"Follow-up added: {form.instance.description}"
        )
        messages.success(self.request, "Follow-up added.")
        return resp

    def get_success_url(self):
        return reverse("cases:detail", kwargs={"pk": self.case.pk})


class FollowUpCompleteView(CasesAccessMixin, DetailView):
    """Mark a follow-up as complete."""
    model = CaseFollowUp
    template_name = "cases/followup_complete.html"

    def get_object(self, queryset=None):
        return get_object_or_404(CaseFollowUp, pk=self.kwargs["followup_pk"], case__pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        followup = self.get_object()
        followup.is_completed = True
        followup.completed_at = timezone.now()
        followup.save()
        log_case_action(
            followup.case, request.user, "followup_completed",
            f"Follow-up completed: {followup.description}"
        )
        messages.success(request, "Follow-up marked as completed.")
        return redirect("cases:detail", pk=followup.case.pk)


# --- Case Status ---

class CaseStatusUpdateView(CasesAccessMixin, FormView):
    """Update the status of a case."""
    template_name = "cases/status_form.html"
    form_class = CaseStatusForm

    def dispatch(self, request, *args, **kwargs):
        self.case = get_object_or_404(Case, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"status": self.case.status}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["case"] = self.case
        return ctx

    def form_valid(self, form):
        new_status = form.cleaned_data["status"]
        old_status = self.case.status
        self.case.status = new_status
        self.case.save()
        log_case_action(
            self.case, self.request.user, "status_changed",
            f"Status: {old_status} → {new_status}"
        )
        messages.success(self.request, f"Status updated to {new_status}.")
        return redirect("cases:detail", pk=self.case.pk)


# --- Case History ---

class CaseHistoryView(CasesAccessMixin, DetailView):
    """Display action history/audit log for a case."""
    model = Case
    template_name = "cases/history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = self.object.action_logs.select_related("user").all()
        return ctx


# --- Prospect to Case Conversion ---

class ConvertProspectToCaseView(AdminRequiredMixin, FormView):
    """Convert a qualified prospect into a tracked case."""
    template_name = "cases/convert.html"
    form_class = ConvertProspectForm

    def dispatch(self, request, *args, **kwargs):
        self.prospect = get_object_or_404(Prospect, pk=self.kwargs["prospect_pk"])
        # Check if already converted
        if hasattr(self.prospect, 'case'):
            messages.warning(request, "This prospect has already been converted to a case.")
            return redirect("prospects:detail", pk=self.prospect.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prospect"] = self.prospect
        return ctx

    def form_valid(self, form):
        contract_date = form.cleaned_data.get("contract_date")
        contract_notes = form.cleaned_data.get("contract_notes")

        # Create the case
        case = Case.objects.create(
            prospect=self.prospect,
            case_type=self.prospect.prospect_type,
            county=self.prospect.county,
            property_address=self.prospect.property_address,
            case_number=self.prospect.case_number,
            parcel_id=self.prospect.parcel_id,
            contract_date=contract_date,
            contract_notes=contract_notes,
            assigned_to=self.prospect.assigned_to,
        )

        # Update prospect workflow_status to converted
        self.prospect.workflow_status = "converted"
        self.prospect.save()

        # Log both prospect and case actions
        from apps.prospects.models import log_prospect_action
        log_prospect_action(
            self.prospect, self.request.user, "converted_to_case",
            f"Converted to Case #{case.pk}"
        )
        log_case_action(
            case, self.request.user, "converted_from_prospect",
            f"Created from Prospect {self.prospect.case_number}"
        )

        messages.success(self.request, f"Case #{case.pk} created successfully from prospect.")
        return redirect("cases:detail", pk=case.pk)


# --- My Cases ---

class MyCasesView(CasesAccessMixin, FilterView):
    """View all cases assigned to the current user."""
    model = Case
    template_name = "cases/list.html"
    filterset_class = CaseFilter
    paginate_by = 25

    def get_queryset(self):
        return Case.objects.filter(
            assigned_to=self.request.user
        ).select_related("prospect", "prospect__county", "prospect__county__state", "assigned_to")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "My Cases"
        return ctx
