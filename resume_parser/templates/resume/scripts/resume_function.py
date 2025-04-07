
import json
import os
import re

import fitz
import pandas as pd
import phonenumbers
from numpy import array
from google.cloud import vision
from sqlalchemy import create_engine

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "resume_parser/templates/resume/scripts/test-resume-parser-8601b5d2664b.json"


class ResumeParser:
    def __init__(self, dictionary_path):
        with open(dictionary_path) as file:
            self.dictionary = json.load(file)

    def extract_names(self, text):
        names = []
        cleaned_text = re.sub(r"\s+", " ", text).strip()

        for name in self.dictionary["name_list"]:
            pattern = rf"\b{re.escape(name)}\b"
            if re.search(pattern, cleaned_text, flags=re.IGNORECASE):
                names.append(name)
        return names

    def extract_skills(self, text):
        skills = []
        cleaned_text = re.sub(r"\s+", " ", text).strip()

        for skill in self.dictionary["skills"]:
            skill_name = skill["name"]
            variants = skill.get("variants", [])
            if variants:
                pattern = r"\b(?:{})\b".format("|".join([re.escape(variant) for variant in variants]))
                if re.search(pattern, cleaned_text, flags=re.IGNORECASE):
                    skills.append(skill_name)
        return skills

    def extract_educations(self, text):
        educations = []
        cleaned_text = re.sub(r"\s+", " ", text).strip()

        for education in self.dictionary["educations"]:
            education_name = education["name"]
            variants = education.get("variants", [])
            if variants:
                pattern = r"\b(?:{})\b".format("|".join([re.escape(variant) for variant in variants]))
                if re.search(pattern, cleaned_text, flags=re.IGNORECASE):
                    educations.append(education_name)
        return educations

    def read_text_from_pdf(self, pdf_path):
        client = vision.ImageAnnotatorClient()

        pdf_file = fitz.open(pdf_path)
        content = ""

        for page in pdf_file:
            pix = page.get_pixmap()
            image_data = pix.tobytes()
            input_image = vision.Image(content=image_data)
            response = client.document_text_detection(image=input_image)
            texts = response.text_annotations

            if texts:
                text = texts[0].description
                content += text + "\n"

        pdf_file.close()

        return content

    def extract_phone_numbers(self, text):
        numbers = []
        cleaned_text = re.sub(r"[^a-zA-Z0-9\s]", "", text)

        for match in phonenumbers.PhoneNumberMatcher(cleaned_text, "MY"):
            numbers.append(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164))
        return numbers[0] if numbers else None

    def extract_email(self, text):
        cleaned_text = re.sub(r"\s+", " ", text.strip())
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", cleaned_text)
        return email_match.group() if email_match else None

    def extract_resume_details(self, pdf_file_path):
        text = self.read_text_from_pdf(pdf_file_path)
        phone_number = self.extract_phone_numbers(text)
        email = self.extract_email(text.lower())
        skills = self.extract_skills(text)
        educations = self.extract_educations(text)
        names = self.extract_names(text)

        return {
            "path": pdf_file_path,
            "name": names[0] if names else None,
            "phone_number": phone_number,
            "email": email,
            "skills": skills,
            "educations": educations,
        }
    def save_resume_data(self, resume_data, db_connection_string):
        # Convert resume_data to a list of dictionaries
        resume_data_list = [resume_data]

        # Initialize empty lists for storing extracted information
        all_names = []
        all_skills = []
        all_educations = []
        all_phone_numbers = []
        all_emails = []

        # Extract data from resume_data_list and store in lists
        for data in resume_data_list:
            all_names.append(data["name"])
            all_phone_numbers.append(data["phone_number"])
            all_emails.append(data["email"])
            all_skills.append(data["skills"])
            all_educations.append(data["educations"])

        # Flatten the lists and remove square brackets for names
        all_names = [name[0] if name else None for name in all_names]

        # Format the skills and educations arrays
        all_skills = [skill if isinstance(skill, list) else [skill] for skill in all_skills]
        all_educations = [education if isinstance(education, list) else [education] for education in all_educations]

        # Create a pandas DataFrame
        candidate_details = {
            "path": [resume_data["path"]],
            "name": [data["name"]],
            "phone_number": all_phone_numbers,
            "email": all_emails,
            "skills": all_skills,
            "educations": all_educations,
        }
        detail_extraction = pd.DataFrame(candidate_details)

        # Connect to the database
        engine = create_engine(db_connection_string)

        # Insert the data into the "resume" table
        detail_extraction.to_sql("users_resume", con=engine, if_exists="append", index=False)

    # def save_resume_data(self, resume_data, db_connection_string):
    #     # Convert resume_data to a list of dictionaries
    #     resume_data_list = [resume_data]

    #     # Initialize empty lists for storing extracted information
    #     all_names = []
    #     all_skills = []
    #     all_educations = []
    #     all_phone_numbers = []
    #     all_emails = []

    #     # Extract data from resume_data_list and store in lists
    #     for data in resume_data_list:
    #         all_names.append(data["name"])
    #         all_phone_numbers.append(data["phone_number"])
    #         all_emails.append(data["email"])
    #         all_skills.append(data["skills"])
    #         all_educations.append(data["educations"])

    #     # Flatten the lists and remove square brackets for names
    #     all_names = [name[0] if name else None for name in all_names]

    #     # Create a pandas DataFrame
    #     candidate_details = {
    #         "path": [resume_data["path"]],
    #         "name": [data["name"]],
    #         "phone_number": all_phone_numbers,
    #         "email": all_emails,
    #         "skills": all_skills,
    #         "educations": all_educations,
    #     }
    #     detail_extraction = pd.DataFrame(candidate_details)

    #     # Print the DataFrame
    #     # print(detail_extraction)

    #     # Connect to the database
    #     engine = create_engine(db_connection_string)

    #     # Insert the data into the "resume" table
    #     detail_extraction.to_sql("users_resume", con=engine, if_exists="append", index=False)
