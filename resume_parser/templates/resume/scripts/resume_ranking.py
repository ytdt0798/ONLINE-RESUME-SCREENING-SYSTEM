import nltk
from resume_parser.users.models import Resume
nltk.download('stopwords')
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances
import numpy as np


def find_top_candidates(job_description, num_candidates=5):
    # Retrieve candidate profiles from the database
    candidate_profiles = Resume.objects.all()

    # Prepare a list to store the top candidates with their details
    top_candidates_with_details = []

    # Tokenize the job description
    tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
    stop_words = set(stopwords.words('english'))  # Set of English stop words
    job_tokens = [token for token in tokenizer.tokenize(job_description.lower()) if token not in stop_words]

    # Create TF-IDF vectors for job description and candidate profiles
    vectorizer = TfidfVectorizer()
    job_vector = vectorizer.fit_transform([' '.join(job_tokens)])
    candidate_vectors = vectorizer.transform([f"Skills: {profile.skills}, Educations: {profile.educations}"
                                              for profile in candidate_profiles])

    # Calculate cosine distances for each candidate profile
    distances = cosine_distances(job_vector, candidate_vectors)

    # Find the top matching candidates
    top_candidates_indices = distances.argsort(axis=1).flatten()[:num_candidates]  # Get the indices of top candidates

    for i in top_candidates_indices:
        candidate_profile = candidate_profiles[i.item()]
        candidate_details = {
            'pk': candidate_profile.pk,
            'path': candidate_profile.path,
            'name': candidate_profile.name,
            'skills': candidate_profile.skills,
            'educations': candidate_profile.educations,
            'score': (1 - distances[0, i]) * 100  # Calculate the score and convert to percentage
        }
        top_candidates_with_details.append(candidate_details)


    return top_candidates_with_details