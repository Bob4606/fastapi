from pydantic import BaseModel
from typing import Optional

class Student(BaseModel):
    name: str
    age: int
    grade: str

class UpdateStudent(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = None
