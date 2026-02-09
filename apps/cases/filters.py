import django_filters
from django import forms

from .models import Case


class CaseFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
        label="Created From",
    )
    created_to = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
        label="Created To",
    )

    class Meta:
        model = Case
        fields = [
            "case_type",
            "status",
            "assigned_to",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.filters.items():
            if hasattr(f, "field") and hasattr(f.field, "widget"):
                widget = f.field.widget
                if isinstance(widget, forms.Select):
                    widget.attrs.setdefault("class", "form-select form-select-sm")
