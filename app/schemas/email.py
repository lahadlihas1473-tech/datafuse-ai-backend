from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=3)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):

        if not isinstance(value, str):
            raise ValueError("Email must be a string")

        value = value.strip()

        if not value:
            raise ValueError("Email is required")

        # No spaces anywhere
        if any(char.isspace() for char in value):
            raise ValueError("Email cannot contain spaces")

        # Exactly one @
        if value.count("@") != 1:
            raise ValueError("Email must contain exactly one @")

        local_part, domain = value.split("@")

        if not local_part:
            raise ValueError("Email must contain text before @")

        if not domain:
            raise ValueError("Email must contain a domain after @")

        if "." not in domain:
            raise ValueError("Email domain must contain a dot")

        if ".." in value:
            raise ValueError("Email cannot contain consecutive dots")

        if domain.startswith("."):
            raise ValueError("Email domain cannot start with a dot")

        if domain.endswith("."):
            raise ValueError("Email domain cannot end with a dot")

        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):

        value = value.strip()

        if not value:
            raise ValueError("Name is required")

        if len(value) < 3:
            raise ValueError("Name must be at least 3 characters long")

        return value