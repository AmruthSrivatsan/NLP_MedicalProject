from pydantic import BaseModel
from typing import List, Optional

class TestResult(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None

class Patient(BaseModel):
    name: Optional[str]
    age: Optional[str]
    sex: Optional[str] = None
    id: Optional[str] = None
    dob: Optional[str] = None
    visit_id: Optional[str] = None

class Report(BaseModel):
    patient: Patient
    tests: List[TestResult]
