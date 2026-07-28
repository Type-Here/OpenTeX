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


class CompileBenchmarkResult(BaseModel):
    """Mean duration of each LaTeX compilation phase over `runs` measured runs."""

    project_title: str
    runs: int
    db_ms: float
    io_ms: float
    tex_ms: float
    total_ms: float
    db_pct: float
    io_pct: float
    tex_pct: float
