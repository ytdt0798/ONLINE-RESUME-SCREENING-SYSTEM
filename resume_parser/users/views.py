import json
import mimetypes
import os
import re

import fitz
import pandas as pd
import phonenumbers
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.validators import FileExtensionValidator
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import filesizeformat
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView,DeleteView
from google.cloud import vision
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql

from resume_parser.templates.resume.scripts.resume_function import ResumeParser
from resume_parser.templates.resume.scripts.resume_ranking import find_top_candidates
from resume_parser.users.models import Resume

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "resume_parser/templates/resume/scripts/test-resume-parser-8601b5d2664b.json"

import os

from django.views.generic import DetailView, ListView
from django.http import FileResponse
from django.views import View
from django.db.models import Q
User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert self.request.user.is_authenticated  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB


class UploadResumeForm(forms.Form):
    # FileField to upload the resume
    resume = forms.FileField(
        label="Upload Resume",
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf"]),  # Only allow PDF files
            lambda file: validate_file_size(file, MAX_FILE_SIZE),  # Validate file size
        ],
    )

class ResumeDataForm(forms.Form):
    # Define form fields based on the resume data structure
    # For example:
    name = forms.CharField(label="Name", max_length=100)
    phone_number = forms.CharField(label="Phone", max_length=20)
    email = forms.EmailField(label="Email")
    skills = forms.CharField(label="Skills", widget=forms.Textarea)
    educations = forms.CharField(label="Educations", widget=forms.Textarea)
    resume_path = forms.CharField(widget=forms.HiddenInput(), required=False)  # Add resume_path field

    def clean_skills(self):
        skills = self.cleaned_data['skills']
        # Remove brackets [] and single quotes from skills
        skills = skills.strip("']['").split("', '")
        return skills

    def clean_educations(self):
        educations = self.cleaned_data['educations']
        # Remove brackets [] and single quotes from educations
        educations = educations.strip("']['").split("', '")
        return educations

# Custom validator to check file size
def validate_file_size(file, max_size):
    if file.size > max_size:
        raise forms.ValidationError(f"The file size exceeds the maximum allowed size of {filesizeformat(max_size)}.")


class UploadResumeView(LoginRequiredMixin, SuccessMessageMixin, TemplateView):
    template_name = "upload_resume.html"
    success_url = reverse_lazy("upload-resume")
    success_message = "Resume uploaded successfully."
    dictionary_path = "resume_parser/templates/resume/scripts/dictionary.json"
    db_connection_string = "postgresql://postgres:4334988@127.0.0.1:5432/resume_parser"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = UploadResumeForm()
        context["resume_data_form"] = ResumeDataForm()
        return context


    def post(self, request, *args, **kwargs):
        form = UploadResumeForm(request.POST, request.FILES)
        if form.is_valid():
            resume_file = form.cleaned_data["resume"]

            # Save the resume file to a specific directory on the server
            resume_directory = "resume_storage"
            resume_path = os.path.join(resume_directory, resume_file.name)
            with open(resume_path, "wb") as file:
                for chunk in resume_file.chunks():
                    file.write(chunk)

            # Process the uploaded resume using ResumeParser from Code 2
            parser = ResumeParser(self.dictionary_path)
            resume_data = parser.extract_resume_details(resume_path)

            
            # Render the resume data form for the user to review and edit
            resume_data_form = ResumeDataForm(initial=resume_data)
            resume_data_form.fields['resume_path'].initial =resume_path


            # Render the template with the resume data form
            context = self.get_context_data(**kwargs)
            # context["form"] = resume_data_form
            context["resume_data_form"] = resume_data_form
            context["resume_data"] = resume_data
            # context["resume_path"] = resume_path
            return self.render_to_response(context) 

        else:
            # If the form is invalid, re-render the template with the form and errors
            context = self.get_context_data(**kwargs)
            context["form"] = form
            return self.render_to_response(context)

class ProcessResumeView(LoginRequiredMixin, SuccessMessageMixin, View):
    success_url = reverse_lazy("upload-resume")
    success_message = "Resume data saved successfully."
    dictionary_path = "resume_parser/templates/resume/scripts/dictionary.json"
    db_connection_string = "postgresql://postgres:4334988@127.0.0.1:5432/resume_parser"

    def post(self, request, *args, **kwargs):
        resume_data_form = ResumeDataForm(request.POST)
        if resume_data_form.is_valid():
            resume_data = resume_data_form.cleaned_data

             # Get the resume path from the form data
            resume_path = resume_data.get("resume_path")
            resume_data['path'] = resume_path

            # Process the uploaded resume data and save it
            parser = ResumeParser(self.dictionary_path)
            parser.save_resume_data(resume_data, self.db_connection_string)

            messages.success(request, self.success_message)
            # Redirect the user to a success page or perform any other action
            return redirect(self.success_url)

        else:
            # If the form is invalid, re-render the template with the form and errors
            context = self.get_context_data(**kwargs)
            context["form"] = UploadResumeForm()
            context["resume_data_form"] = resume_data_form
            return self.render_to_response(context)

class ResumeListView(LoginRequiredMixin, ListView):
    template_name = "resume_list.html"
    context_object_name = "resumes"
    resume_directory = "resume_storage"

    def get_queryset(self):
        return Resume.objects.all()
    


class CandidateSearchView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'resume_search.html')

    def post(self, request):
        search_query = request.POST.get('search_query')

        # Perform the search operation based on the search_query
        search_results = Resume.objects.filter(Q(name__icontains=search_query) | Q(skills__icontains=search_query) | Q(educations__icontains=search_query))
        resumes = Resume.objects.all()  # Fetch all resumes

        context = {
            'resumes': resumes,
            'search_results': search_results,
            'search_query': search_query,
        }

        return render(request, 'resume/resume_list.html', context)
        # return render(request, 'resume/resume_search_results.html', {'results': results})


class ResumeDetailView(LoginRequiredMixin, DetailView):
    template_name = "resume/resume_detail.html"
    context_object_name = "resume"
    model = Resume

    def get_object(self, queryset=None):
        resume_pk = self.kwargs["resume_pk"]
        resume = Resume.objects.get(pk=resume_pk)  # Fetch the resume from the database using the primary key (pk)
        return resume


class ResumePreviewView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        resume_pk = kwargs["resume_pk"]
        resume = Resume.objects.get(pk=resume_pk)

        file_path = resume.path
        if not os.path.exists(file_path):
            return HttpResponseForbidden("Resume file not found.")
        response = FileResponse(open(file_path, "rb"), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="resume.pdf"'
        return response

class ResumeDeleteView(LoginRequiredMixin, DeleteView):
    model = Resume
    template_name = 'resume_delete.html'
    success_url = reverse_lazy('resume-list')  # Redirect to the resume list after successful deletion

class CandidateRankingView(LoginRequiredMixin,View):
    def get(self, request):
        return render(request, 'resume/resume_ranking.html')

    def post(self, request):
        job_description = request.POST.get('job_description')
        num_candidates = int(request.POST.get('num_candidates', 5))

        top_candidates_with_details = find_top_candidates(job_description, num_candidates)
        
        context = {
            'job_description': job_description,
            'num_candidates': num_candidates,
            'top_candidates_with_details': top_candidates_with_details,
        }

        return render(request, 'resume/resume_candidates.html', context)
        
    
    @staticmethod
    def resume_preview(request, pk):
        candidate = get_object_or_404(Resume, pk=pk)
        resume_path = candidate.path

        if resume_path:
            try:
                with open(resume_path, 'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/pdf')
                    response['Content-Disposition'] = 'inline; filename=resume.pdf'
                return response
            except FileNotFoundError:
                raise Http404("Resume not found")

        raise Http404("Resume path not available")