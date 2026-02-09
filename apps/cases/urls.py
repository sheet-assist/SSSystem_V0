from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    # Case list and detail
    path("", views.CaseListView.as_view(), name="list"),
    path("<int:pk>/", views.CaseDetailView.as_view(), name="detail"),
    
    # Notes
    path("<int:pk>/notes/add/", views.CaseNoteCreateView.as_view(), name="note_add"),
    
    # Follow-ups
    path("<int:pk>/followups/add/", views.CaseFollowUpCreateView.as_view(), name="followup_add"),
    path("<int:pk>/followups/<int:followup_pk>/complete/", views.FollowUpCompleteView.as_view(), name="followup_complete"),
    
    # Case status
    path("<int:pk>/status/", views.CaseStatusUpdateView.as_view(), name="status_update"),
    
    # History
    path("<int:pk>/history/", views.CaseHistoryView.as_view(), name="history"),
    
    # Conversion from prospect
    path("convert/<int:prospect_pk>/", views.ConvertProspectToCaseView.as_view(), name="convert"),
    
    # My cases
    path("my/", views.MyCasesView.as_view(), name="my_cases"),
]
