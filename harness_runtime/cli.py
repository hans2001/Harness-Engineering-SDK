from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from harness_runtime.adapters import list_adapters
from harness_runtime.harvesters import issue_providers
from harness_runtime.sdk import Harness

app = typer.Typer(help="Repo-native harness runtime for coding-agent workflows.")
console = Console()


def get_harness(repo: Path) -> Harness:
    return Harness(repo=repo)


@app.command()
def init(repo: Path = typer.Option(Path("."), help="Repository root.")) -> None:
    """Create .harness layout and SQLite metadata."""
    harness = get_harness(repo)
    harness.init()
    console.print(f"[green]Initialized harness at[/green] {Path(repo).resolve() / '.harness'}")


@app.command()
def harvest(
    source: Path | None = typer.Option(None, "--from", "-f", help="Local file or directory to harvest."),
    title: str | None = typer.Option(None, help="Manual task title."),
    instructions: str | None = typer.Option(None, help="Manual task instructions."),
    verification: list[str] | None = typer.Option(None, "--verify", help="Manual verification command."),
    issue_provider: str | None = typer.Option(
        None,
        "--issue-provider",
        help="Issue tracker provider such as github, gitlab, or bitbucket when supported.",
    ),
    issue_resource: str | None = typer.Option(
        None,
        "--issue-resource",
        help="Provider-specific resource identifier, such as owner/repo.",
    ),
    issue_token: str | None = typer.Option(
        None,
        "--issue-token",
        help="Provider token. Defaults to the provider's environment variable when supported.",
    ),
    issue_state: str = typer.Option("open", "--issue-state", help="Issue state filter."),
    issue_limit: int = typer.Option(20, "--issue-limit", help="Maximum number of issues to import."),
    issue_comment_limit: int = typer.Option(10, "--issue-comment-limit", help="Maximum number of issue comments to import."),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Ignore cached GitHub responses for this harvest run."),
    github_repo: str | None = typer.Option(None, "--github-repo", help="GitHub repository in owner/name form."),
    github_token: str | None = typer.Option(None, "--github-token", help="GitHub token. Defaults to GITHUB_TOKEN."),
    github_state: str = typer.Option("open", "--github-state", help="GitHub issue state filter."),
    github_limit: int = typer.Option(20, "--github-limit", help="Maximum number of GitHub issues to import."),
    github_comment_limit: int = typer.Option(10, "--github-comment-limit", help="Maximum number of GitHub issue comments to import."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Harvest local files, manual input, or issue-tracker tasks into task specs."""
    harness = get_harness(repo)
    if source is not None:
        tasks = harness.harvest(source=source)
    elif issue_provider is not None:
        if issue_resource is None:
            raise typer.BadParameter("--issue-resource is required with --issue-provider.")
        tasks = harness.harvest_issues(
            provider=issue_provider,
            resource=issue_resource,
            token=issue_token,
            state=issue_state,
            limit=issue_limit,
            comment_limit=issue_comment_limit,
            verification_commands=verification,
            refresh_cache=refresh_cache,
        )
    elif github_repo is not None:
        tasks = harness.harvest_github(
            repo_full_name=github_repo,
            token=github_token,
            state=github_state,
            limit=github_limit,
            comment_limit=github_comment_limit,
            verification_commands=verification,
            refresh_cache=refresh_cache,
        )
    elif title and instructions:
        tasks = [harness.harvest_manual(title, instructions, verification)]
    else:
        raise typer.BadParameter(
            "Provide --from, --issue-provider with --issue-resource, --github-repo, or both --title and --instructions."
        )

    table = Table("Task", "Title", "Source")
    for task in tasks:
        table.add_row(task.id, task.title, str(task.source))
    console.print(table)


@app.command("providers")
def list_providers() -> None:
    """List supported issue-harvest providers."""
    table = Table("Provider", "Token Env Var")
    for provider in issue_providers().values():
        table.add_row(provider.name, provider.env_token_var)
    console.print(table)


@app.command("cache")
def cache_command(
    target: str = typer.Argument("github", help="Cache namespace."),
    clear: bool = typer.Option(False, "--clear", help="Delete cached entries for the namespace."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Inspect or clear local harness caches."""
    if target != "github":
        raise typer.BadParameter("Supported cache namespaces: github")
    harness = get_harness(repo)
    if clear:
        removed = harness.clear_github_cache()
        console.print(f"Removed GitHub cache entries: {removed}")
        return
    stats = harness.github_cache_stats()
    table = Table("Namespace", "Entries", "Bytes")
    table.add_row("github", str(stats["entries"]), str(stats["bytes"]))
    console.print(table)


@app.command("adapters")
def adapters_command() -> None:
    """List supported agent adapters."""
    table = Table("Adapter")
    for adapter_name in list_adapters():
        table.add_row(adapter_name)
    console.print(table)


@app.command()
def preflight(
    task_id: str | None = typer.Argument(None, help="Task id to inspect."),
    command: list[str] | None = typer.Option(None, "--command", help="Ad hoc command to inspect."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Check whether verification executables are available locally."""
    if task_id is None and not command:
        raise typer.BadParameter("Provide a task id or at least one --command.")
    result = get_harness(repo).preflight(task_id=task_id, commands=command)
    table = Table("Command", "Executable", "Available", "Message")
    for item in result.commands:
        table.add_row(item.command, item.executable or "-", str(item.available), item.message)
    console.print(table)
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("dataset")
def dataset_command(
    kind: str = typer.Option("github-linked-prs", "--kind", help="Dataset builder kind."),
    repo_filter: str | None = typer.Option(None, "--repo-filter", help="Only include tasks from this repo_full_name."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of dataset entries to emit."),
    materialize_tasks: bool = typer.Option(False, "--materialize-tasks", help="Write runnable eval tasks from the dataset."),
    target_repo_path: str | None = typer.Option(None, "--target-repo-path", help="repo_path to place into generated eval tasks."),
    verification: list[str] | None = typer.Option(None, "--verify", help="Override verification commands for materialized tasks."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Build local eval datasets from harvested tasks."""
    harness = get_harness(repo)
    if kind != "github-linked-prs":
        raise typer.BadParameter("Supported dataset kinds: github-linked-prs")
    entries = harness.build_github_eval_dataset(repo_filter=repo_filter, limit=limit)
    console.print(f"Dataset entries: {len(entries)}")
    console.print(f"Output: {Path(repo).resolve() / '.harness' / 'datasets' / 'github_linked_pr_eval.jsonl'}")
    if materialize_tasks:
        if not target_repo_path:
            raise typer.BadParameter("--target-repo-path is required with --materialize-tasks.")
        tasks = harness.materialize_eval_tasks(
            target_repo_path=target_repo_path,
            repo_filter=repo_filter,
            verification_commands=verification,
            limit=limit,
        )
        console.print(f"Materialized tasks: {len(tasks)}")
        console.print(f"Task output: {Path(repo).resolve() / '.harness' / 'tasks' / 'generated'}")


@app.command("benchmark")
def benchmark_command(
    repo_filter: str = typer.Option(..., "--repo-filter", help="Repository full name to benchmark."),
    target_repo_path: str = typer.Option(..., "--target-repo-path", help="Target repo checkout to benchmark against."),
    adapter: str = typer.Option("shell", "--adapter", help="Agent adapter to use."),
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent command for adapters that require one."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of tasks to run."),
    verification: list[str] | None = typer.Option(None, "--verify", help="Override verification commands."),
    timeout: int | None = typer.Option(None, help="Agent timeout in seconds."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Run a reference-backed benchmark loop for harvested GitHub tasks."""
    summary = get_harness(repo).benchmark(
        repo_filter=repo_filter,
        target_repo_path=target_repo_path,
        adapter=adapter,
        agent=agent,
        limit=limit,
        verification_commands=verification,
        timeout=timeout,
    )
    console.print(f"Benchmark: {summary.benchmark_id}")
    console.print(f"Tasks: {summary.total_tasks}")
    console.print(f"Executed runs: {summary.executed_runs}")
    console.print(f"Verified runs: {summary.verified_runs}")
    console.print(f"Passed runs: {summary.passed_runs}")
    if summary.report_path:
        console.print(f"Report: {summary.report_path}")


flywheel_app = typer.Typer(help="Closed-loop harness improvement flywheel.")
app.add_typer(flywheel_app, name="flywheel")


@flywheel_app.command("run")
def flywheel_run_command(
    repo_filter: str = typer.Option(..., "--repo-filter", help="Repository full name to train against."),
    target_repo_path: str = typer.Option(..., "--target-repo-path", help="Target repo checkout."),
    adapter: str = typer.Option("shell", "--adapter", help="Agent adapter to use."),
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent command for adapters that require one."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of tasks per round."),
    verification: list[str] | None = typer.Option(None, "--verify", help="Override verification commands."),
    timeout: int | None = typer.Option(None, help="Agent timeout in seconds."),
    rounds: int = typer.Option(2, "--rounds", help="Maximum flywheel rounds to execute."),
    no_auto_promote: bool = typer.Option(False, "--no-auto-promote", help="Propose patches without writing skills."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Run benchmark rounds, analyze failures, and promote harness skills."""
    summary = get_harness(repo).flywheel(
        repo_filter=repo_filter,
        target_repo_path=target_repo_path,
        adapter=adapter,
        agent=agent,
        limit=limit,
        verification_commands=verification,
        timeout=timeout,
        rounds=rounds,
        auto_promote=not no_auto_promote,
    )
    console.print(f"Flywheel: {summary.flywheel_id}")
    console.print(f"Initial pass rate: {summary.initial_pass_rate:.1%}")
    console.print(f"Final pass rate: {summary.final_pass_rate:.1%}")
    console.print(f"Rounds: {len(summary.rounds)}")
    if summary.report_path:
        console.print(f"Report: {summary.report_path}")


@flywheel_app.command("analyze")
def flywheel_analyze_command(
    benchmark_id: str = typer.Option("latest", "--benchmark-id", help="Benchmark summary id to analyze."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Propose harness patches from a benchmark summary."""
    patches = get_harness(repo).analyze_flywheel(benchmark_id)
    table = Table("Patch", "Title", "Status", "Target")
    for patch in patches:
        table.add_row(patch.patch_id, patch.title, str(patch.status), patch.target_path)
    console.print(table)


@flywheel_app.command("promote")
def flywheel_promote_command(
    patch_id: str = typer.Argument(..., help="Harness patch id to promote into .harness/skills/."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Promote a proposed harness patch into the active skills layer."""
    patch = get_harness(repo).promote_patch(patch_id)
    console.print(f"Promoted: {patch.patch_id}")
    console.print(f"Skill: {patch.target_path}")


@flywheel_app.command("status")
def flywheel_status_command(
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Show active skills, patches, and the latest flywheel summary."""
    status = get_harness(repo).flywheel_status()
    skills = status.get("skills") or []
    console.print(f"Skills: {', '.join(skills) if skills else 'none'}")
    latest = status.get("latest")
    if latest:
        console.print(f"Latest flywheel: {latest['flywheel_id']}")
        console.print(f"Final pass rate: {latest['final_pass_rate']:.1%}")
    patches = status.get("patches") or []
    console.print(f"Patches tracked: {len(patches)}")


@app.command()
def run(
    task_id: str,
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent command to execute."),
    adapter: str = typer.Option("shell", "--adapter", help="Agent adapter to use."),
    timeout: int | None = typer.Option(None, help="Agent timeout in seconds."),
    keep_workspace: bool = typer.Option(
        True,
        "--keep-workspace/--cleanup",
        help="Keep the isolated workspace for later verification, or remove it after run.",
    ),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Run one task in an isolated workspace."""
    record = get_harness(repo).run(
        task_id=task_id,
        agent=agent,
        adapter=adapter,
        timeout=timeout,
        keep_workspace=keep_workspace,
    )
    console.print(f"[bold]Run:[/bold] {record.id}")
    console.print(f"[bold]Status:[/bold] {record.status}")
    console.print(f"[bold]Artifacts:[/bold] {record.artifact_path}")


@app.command()
def verify(
    run_id: str,
    cleanup: bool = typer.Option(False, "--cleanup", help="Remove the workspace after verification."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Run configured verification commands for a run."""
    try:
        result = get_harness(repo).verify(run_id=run_id, cleanup=cleanup)
    except (KeyError, FileNotFoundError) as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"[bold]Run:[/bold] {result.run_id}")
    console.print(f"[bold]Passed:[/bold] {result.passed}")
    for command in result.commands:
        suffix = f", reason={command.failure_reason}" if command.failure_reason else ""
        console.print(f"- {command.command}: exit={command.exit_code}, {command.duration_seconds:.2f}s{suffix}")


@app.command("runs")
def list_runs(repo: Path = typer.Option(Path("."), help="Repository root.")) -> None:
    """List known runs and artifact paths."""
    table = Table("Run", "Task", "Status", "Artifacts")
    for run_record in get_harness(repo).runs():
        table.add_row(run_record.id, run_record.task_id, str(run_record.status), run_record.artifact_path)
    console.print(table)


@app.command("eval")
def eval_command(
    agent: str | None = typer.Option(None, "--agent", "-a", help="Run all harvested tasks first."),
    adapter: str = typer.Option("shell", "--adapter", help="Agent adapter to use for eval runs."),
    timeout: int | None = typer.Option(None, help="Agent timeout in seconds."),
    repo: Path = typer.Option(Path("."), help="Repository root."),
) -> None:
    """Run an eval batch when --agent is provided, then aggregate results."""
    summary = get_harness(repo).eval(agent=agent, adapter=adapter, timeout=timeout)
    console.print(f"Total runs: {summary.total_runs}")
    console.print(f"Verified runs: {summary.verified_runs}")
    console.print(f"Pass rate: {summary.pass_rate:.1%}")


@app.command()
def report(repo: Path = typer.Option(Path("."), help="Repository root.")) -> None:
    """Generate a local Markdown report."""
    path = get_harness(repo).report()
    console.print(f"[green]Report written:[/green] {path}")


if __name__ == "__main__":
    app()
