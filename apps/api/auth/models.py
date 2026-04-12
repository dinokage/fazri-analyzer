from enum import Enum
from typing import Optional
from pydantic import BaseModel


class UserRole(str, Enum):
    """User role enum matching Prisma UserRole"""
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    FACULTY = "FACULTY"
    SUPER_ADMIN = "SUPER_ADMIN"


class AuthenticatedUser(BaseModel):
    """Authenticated user model from JWT claims"""
    id: str
    entity_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: UserRole
    face_id: Optional[str] = None
    student_id: Optional[str] = None
    staff_id: Optional[str] = None
    department: Optional[str] = None
    organizationId: Optional[str] = None
    sessionId: Optional[str] = None
