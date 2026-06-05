from pydantic import BaseModel


class DepartmentStat(BaseModel):
    department: str
    project_count: int
    total_collaborators: int
    avg_collaborators: float
    total_activity: int


class BenchmarkResult(BaseModel):
    label: str
    with_ms: float
    without_ms: float
    speedup: float
