from django.urls import path

from . import views

urlpatterns = [
    path("sessions/", views.SessionCreateView.as_view(), name="session-create"),
    path(
        "sessions/<uuid:session_id>/question/",
        views.QuestionView.as_view(),
        name="session-question",
    ),
    path("sessions/<uuid:session_id>/answer/", views.AnswerView.as_view(), name="session-answer"),
    path("sessions/<uuid:session_id>/result/", views.ResultView.as_view(), name="session-result"),
    path(
        "sessions/<uuid:session_id>/submit-score/",
        views.SubmitScoreView.as_view(),
        name="session-submit-score",
    ),
]
