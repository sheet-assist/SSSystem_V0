from django import forms
from django.contrib.auth import get_user_model

from apps.locations.models import State, County
from apps.prospects.models import Prospect

User = get_user_model()


class ScrapeTriggerForm(forms.Form):
    """Form to trigger a new scrape job."""
    
    PROSPECT_TYPE_CHOICES = [
        ('TD', 'Tax Deed'),
        ('TL', 'Tax Lien'),
        ('SS', 'Sheriff Sale'),
        ('MF', 'Mortgage Foreclosure'),
    ]
    
    state = forms.ModelChoiceField(
        queryset=State.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_state"}),
        label="State"
    )
    
    county = forms.ModelChoiceField(
        queryset=County.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="County",
        required=False,
    )
    
    prospect_type = forms.ChoiceField(
        choices=PROSPECT_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Prospect Type"
    )
    
    target_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Auction Date"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If state is provided, filter counties
        if 'state' in self.data and self.data['state']:
            try:
                state_id = int(self.data['state'])
                self.fields['county'].queryset = County.objects.filter(
                    state_id=state_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        county = cleaned_data.get('county')
        
        if not county:
            raise forms.ValidationError("County is required.")
        
        return cleaned_data
