import os

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CharField, EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from config import settings
from resume_parser.users.managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Resume Parser.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class Resume(models.Model):
    path = models.TextField(max_length=100)
    name = models.TextField(max_length=255)
    phone_number = models.TextField(max_length=20)
    email = models.TextField()
    skills = ArrayField(models.TextField())
    educations = ArrayField(models.TextField())

    def __str__(self):
        return self.name

    @property
    def file_path(self):
        return os.path.join(settings.SECURE_RESUME_DIR, self.path)
    
    def delete(self, *args, **kwargs):
        # Remove the associated file when the Resume instance is deleted
        if self.path:
            # Get the file path
            file_path = self.path
            # Delete the file from the file system
            if os.path.exists(file_path):
                os.remove(file_path)

        super().delete(*args, **kwargs)
