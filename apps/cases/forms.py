from django import forms
from django.contrib.auth import get_user_model

from .models import Case, CaseNote, CaseFollowUp

User = get_user_model()


class ConvertProspectForm(forms.Form):
    contract_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    contract_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}))
    assigned_to = forms.IntegerField(required=False, widget=forms.HiddenInput())


class CaseNoteForm(forms.ModelForm):
    class Meta:
        model = CaseNote
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class CaseFollowUpForm(forms.ModelForm):
    class Meta:
        model = CaseFollowUp
        fields = ["assigned_to", "due_date", "description"]
        widgets = {
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class CaseStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=Case.CASE_STATUS,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
