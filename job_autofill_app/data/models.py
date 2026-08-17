"""Data models for the Job Auto-Fill application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class Profile:
    """User profile containing all information needed for job applications."""
    id: int = 0
    full_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    links: dict = field(default_factory=lambda: {"linkedin": "", "github": "", "portfolio": "", "other": ""})
    education: list = field(default_factory=list)  # [{school, degree, field, start, end, gpa}]
    experience: list = field(default_factory=list)  # [{company, title, start, end, description}]
    skills: list = field(default_factory=list)
    resume_path: str = ""
    cover_letter_template: str = ""
    qa_bank: dict = field(default_factory=dict)  # {question_text: answer_text}

    def to_dict(self) -> dict:
        """Convert profile to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "links": self.links,
            "education": self.education,
            "experience": self.experience,
            "skills": self.skills,
            "resume_path": self.resume_path,
            "cover_letter_template": self.cover_letter_template,
            "qa_bank": self.qa_bank,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create profile from dictionary."""
        return cls(
            id=data.get("id", 0),
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            country=data.get("country", ""),
            links=data.get("links", {"linkedin": "", "github": "", "portfolio": "", "other": ""}),
            education=data.get("education", []),
            experience=data.get("experience", []),
            skills=data.get("skills", []),
            resume_path=data.get("resume_path", ""),
            cover_letter_template=data.get("cover_letter_template", ""),
            qa_bank=data.get("qa_bank", {}),
        )


@dataclass
class JobListing:
    """Represents a scraped job listing."""
    id: int = 0
    source_url: str = ""
    apply_url: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    employment_type: str = ""
    salary: str = ""
    date_scraped: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "New"  # New / Applied / Skipped

    def to_dict(self) -> dict:
        """Convert job listing to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_url": self.source_url,
            "apply_url": self.apply_url,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "employment_type": self.employment_type,
            "salary": self.salary,
            "date_scraped": self.date_scraped,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobListing":
        """Create job listing from dictionary."""
        return cls(
            id=data.get("id", 0),
            source_url=data.get("source_url", ""),
            apply_url=data.get("apply_url", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            description=data.get("description", ""),
            employment_type=data.get("employment_type", ""),
            salary=data.get("salary", ""),
            date_scraped=data.get("date_scraped", datetime.now().isoformat()),
            status=data.get("status", "New"),
        )