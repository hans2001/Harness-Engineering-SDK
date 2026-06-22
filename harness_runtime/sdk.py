from __future__ import annotations

from pathlib import Path

from harness_runtime.config import init_layout
from harness_runtime.datasets import build_eval_summary, build_github_reference_dataset, materialize_eval_tasks
from harness_runtime.harvesters import (
    clear_github_cache,
    create_manual_task,
    get_issue_provider,
    github_cache_stats,
    harvest_github_issues,
    harvest_local,
)
from harness_runtime.preflight import run_preflight, task_preflight
from harness_runtime.reports import generate_report
from harness_runtime.runners import run_task
from harness_runtime.schemas import (
    BenchmarkSummary,
    EvalDatasetEntry,
    EvalSummary,
    FlywheelSummary,
    HarnessPatch,
    PreflightResult,
    RunRecord,
    TaskSpec,
    VerificationResult,
    load_task,
)
from harness_runtime.storage import Storage
from harness_runtime.verification import verify_run


class Harness:
    def __init__(self, repo: str | Path = "."):
        self.repo = Path(repo).resolve()

    def init(self) -> None:
        init_layout(self.repo)
        Storage(self.repo)

    def harvest(self, source: str | Path = "tasks") -> list[TaskSpec]:
        return harvest_local(self.repo, Path(source))

    def harvest_github(
        self,
        repo_full_name: str,
        token: str | None = None,
        state: str = "open",
        limit: int = 20,
        comment_limit: int = 10,
        verification_commands: list[str] | None = None,
        refresh_cache: bool = False,
    ) -> list[TaskSpec]:
        return harvest_github_issues(
            self.repo,
            repo_full_name=repo_full_name,
            token=token,
            state=state,
            limit=limit,
            comment_limit=comment_limit,
            verification_commands=verification_commands,
            refresh_cache=refresh_cache,
        )

    def harvest_issues(
        self,
        provider: str,
        resource: str,
        token: str | None = None,
        state: str = "open",
        limit: int = 20,
        comment_limit: int = 10,
        verification_commands: list[str] | None = None,
        refresh_cache: bool = False,
    ) -> list[TaskSpec]:
        issue_provider = get_issue_provider(provider)
        return issue_provider.harvest(
            self.repo,
            resource,
            token,
            state,
            limit,
            comment_limit,
            verification_commands,
            refresh_cache,
        )

    def harvest_manual(
        self,
        title: str,
        instructions: str,
        verification_commands: list[str] | None = None,
    ) -> TaskSpec:
        return create_manual_task(self.repo, title, instructions, verification_commands)

    def run(
        self,
        task_id: str,
        agent: str | None = None,
        adapter: str = "shell",
        timeout: int | None = None,
        keep_workspace: bool = True,
    ) -> RunRecord:
        task = self.load_task(task_id)
        return run_task(
            self.repo,
            task,
            agent,
            adapter_name=adapter,
            timeout=timeout,
            keep_workspace=keep_workspace,
        )

    def verify(self, run_id: str, cleanup: bool = False) -> VerificationResult:
        storage = Storage(self.repo)
        resolved_run_id = storage.resolve_run_id(run_id)
        run = storage.get_run(resolved_run_id)
        task = self.load_task(run.task_id)
        return verify_run(self.repo, resolved_run_id, task, cleanup=cleanup)

    def preflight(self, task_id: str | None = None, commands: list[str] | None = None) -> PreflightResult:
        if task_id is not None:
            return task_preflight(self.repo, self.load_task(task_id))
        return run_preflight(self.repo, commands or [])

    def runs(self) -> list[RunRecord]:
        return Storage(self.repo).list_runs()

    def eval(
        self,
        agent: str | None = None,
        adapter: str = "shell",
        timeout: int | None = None,
    ) -> EvalSummary:
        if agent or adapter != "shell":
            for task in Storage(self.repo).list_tasks():
                run = self.run(task.id, agent=agent, adapter=adapter, timeout=timeout)
                self.verify(run.id, cleanup=True)
        return build_eval_summary(self.repo)

    def build_github_eval_dataset(
        self,
        repo_filter: str | None = None,
        limit: int | None = None,
    ) -> list[EvalDatasetEntry]:
        return build_github_reference_dataset(self.repo, repo_filter=repo_filter, limit=limit)

    def materialize_eval_tasks(
        self,
        target_repo_path: str,
        repo_filter: str | None = None,
        verification_commands: list[str] | None = None,
        limit: int | None = None,
    ) -> list[TaskSpec]:
        return materialize_eval_tasks(
            self.repo,
            repo_filter=repo_filter,
            target_repo_path=target_repo_path,
            verification_commands=verification_commands,
            limit=limit,
        )

    def report(self) -> Path:
        return generate_report(self.repo)

    def github_cache_stats(self) -> dict[str, int]:
        return github_cache_stats(self.repo)

    def clear_github_cache(self) -> int:
        return clear_github_cache(self.repo)

    def benchmark(
        self,
        *,
        repo_filter: str,
        target_repo_path: str,
        adapter: str,
        agent: str | None = None,
        limit: int | None = None,
        verification_commands: list[str] | None = None,
        timeout: int | None = None,
    ) -> BenchmarkSummary:
        from harness_runtime.benchmark import run_reference_benchmark

        return run_reference_benchmark(
            self.repo,
            repo_filter=repo_filter,
            target_repo_path=target_repo_path,
            adapter=adapter,
            agent=agent,
            limit=limit,
            verification_commands=verification_commands,
            timeout=timeout,
        )

    def analyze_flywheel(self, benchmark_id: str = "latest") -> list[HarnessPatch]:
        from harness_runtime.flywheel import analyze_benchmark_failures, load_benchmark_summary

        summary = load_benchmark_summary(self.repo, benchmark_id)
        return analyze_benchmark_failures(self.repo, summary)

    def promote_patch(self, patch_id: str) -> HarnessPatch:
        from harness_runtime.flywheel import promote_patch

        return promote_patch(self.repo, patch_id)

    def flywheel(
        self,
        *,
        repo_filter: str,
        target_repo_path: str,
        adapter: str,
        agent: str | None = None,
        limit: int | None = None,
        verification_commands: list[str] | None = None,
        timeout: int | None = None,
        rounds: int = 2,
        auto_promote: bool = True,
    ) -> FlywheelSummary:
        from harness_runtime.flywheel import run_flywheel

        return run_flywheel(
            self.repo,
            repo_filter=repo_filter,
            target_repo_path=target_repo_path,
            adapter=adapter,
            agent=agent,
            limit=limit,
            verification_commands=verification_commands,
            timeout=timeout,
            rounds=rounds,
            auto_promote=auto_promote,
        )

    def flywheel_status(self) -> dict[str, object]:
        from harness_runtime.flywheel import flywheel_status

        return flywheel_status(self.repo)

    def load_task(self, task_id: str) -> TaskSpec:
        path = Storage(self.repo).get_task_path(task_id)
        return load_task(path)
