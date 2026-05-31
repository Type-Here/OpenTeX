from pydantic import BaseModel


class DepartmentStat(BaseModel):
    department: str
    project_count: int
    total_collaborators: int
    avg_collaborators: float
    total_activity: int