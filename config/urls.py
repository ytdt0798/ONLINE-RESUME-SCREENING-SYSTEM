from django import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView

from resume_parser.users.views import CandidateRankingView, CandidateSearchView, ProcessResumeView, ResumeDeleteView, ResumeDetailView, ResumeListView, ResumePreviewView, UploadResumeView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("resume_parser.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("upload-resume/", UploadResumeView.as_view(template_name="resume/upload_resume.html"), name="upload-resume"),
    path("process-resume/", ProcessResumeView.as_view(), name="process-resume"),
    path("resumes/", ResumeListView.as_view(template_name="resume/resume_list.html"), name="resume-list"),
    path("resumes/<int:resume_pk>/", ResumeDetailView.as_view(), name="resume_detail"),
    path("resumes/<int:resume_pk>/preview/", ResumePreviewView.as_view(), name="resume_preview"),
    path('resumes/<int:pk>/delete/', ResumeDeleteView.as_view(), name='resume-delete'),
    path('ranking/', CandidateRankingView.as_view(), name='candidate_ranking'),
    path('preview/<int:pk>/', CandidateRankingView.resume_preview, name='resume_preview'),
    path('search/', CandidateSearchView.as_view(), name='candidate_search'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
