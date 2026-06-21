from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from harness_runtime.config import harness_dir
from harness_runtime.schemas import RunRecord, TaskSpec, VerificationResult


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)


class VerificationRow(Base):
    __tablename__ = "verifications"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)


class Storage:
    def __init__(self, repo: Path):
        self.repo = repo
        self.path = harness_dir(repo) / "harness.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.path}", future=True)
        Base.metadata.create_all(self.engine)

    def upsert_task(self, task: TaskSpec, path: Path) -> None:
        with Session(self.engine) as session:
            row = session.get(TaskRow, task.id)
            if row is None:
                row = TaskRow(id=task.id, title=task.title, source=str(task.source), path=str(path), data="")
                session.add(row)
            row.title = task.title
            row.source = str(task.source)
            row.path = str(path)
            row.data = task.model_dump_json()
            session.commit()

    def save_run(self, run: RunRecord) -> None:
        with Session(self.engine) as session:
            row = session.get(RunRow, run.id)
            if row is None:
                row = RunRow(
                    id=run.id,
                    task_id=run.task_id,
                    status=str(run.status),
                    artifact_path=run.artifact_path,
                    data="",
                )
                session.add(row)
            row.task_id = run.task_id
            row.status = str(run.status)
            row.artifact_path = run.artifact_path
            row.data = run.model_dump_json()
            session.commit()

    def save_verification(self, result: VerificationResult) -> None:
        with Session(self.engine) as session:
            row = session.get(VerificationRow, result.run_id)
            if row is None:
                row = VerificationRow(
                    run_id=result.run_id,
                    task_id=result.task_id,
                    passed=int(result.passed),
                    data="",
                )
                session.add(row)
            row.task_id = result.task_id
            row.passed = int(result.passed)
            row.data = result.model_dump_json()
            session.commit()

    def list_runs(self) -> list[RunRecord]:
        with Session(self.engine) as session:
            rows = session.scalars(select(RunRow).order_by(RunRow.id)).all()
        return [RunRecord.model_validate_json(row.data) for row in rows]

    def list_tasks(self) -> list[TaskSpec]:
        with Session(self.engine) as session:
            rows = session.scalars(select(TaskRow).order_by(TaskRow.id)).all()
        return [TaskSpec.model_validate_json(row.data) for row in rows]

    def list_verifications(self) -> list[VerificationResult]:
        with Session(self.engine) as session:
            rows = session.scalars(select(VerificationRow).order_by(VerificationRow.run_id)).all()
        return [VerificationResult.model_validate_json(row.data) for row in rows]

    def get_run(self, run_id: str) -> RunRecord:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
        if row is None:
            raise KeyError(f"Run not found: {run_id}")
        return RunRecord.model_validate_json(row.data)

    def resolve_run_id(self, run_id: str) -> str:
        runs = self.list_runs()
        if run_id == "latest":
            if not runs:
                raise KeyError("No runs have been recorded yet.")
            return runs[-1].id

        exact = [run for run in runs if run.id == run_id]
        if exact:
            return exact[0].id

        prefixed = [run for run in runs if run.id.startswith(run_id)]
        if len(prefixed) == 1:
            return prefixed[0].id
        if len(prefixed) > 1:
            matches = ", ".join(run.id for run in prefixed)
            raise KeyError(f"Run id prefix is ambiguous: {run_id}. Matches: {matches}")

        available = ", ".join(run.id for run in runs[-5:]) or "none"
        raise KeyError(f"Run not found: {run_id}. Recent runs: {available}")

    def get_task_path(self, task_id: str) -> Path:
        with Session(self.engine) as session:
            row = session.get(TaskRow, task_id)
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return Path(row.path)

    def summary_json(self) -> str:
        return json.dumps(
            {
                "runs": [run.model_dump(mode="json") for run in self.list_runs()],
                "verifications": [
                    verification.model_dump(mode="json")
                    for verification in self.list_verifications()
                ],
            },
            indent=2,
        )
