from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from agentic_cfo.ui import backend

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised only when UI extra is missing.
    st = None  # type: ignore[assignment]


NAV_ITEMS = (
    "Dashboard",
    "Experiments",
    "Runs",
    "Results",
    "Data",
    "Audit",
    "Human Audit",
    "Settings",
    "GUI Plan",
)


def _require_streamlit() -> Any:
    if st is None:
        raise RuntimeError('Streamlit is not installed. Install with: python -m pip install -e ".[ui]"')
    return st


def _paths() -> backend.PlatformPaths:
    if "platform_paths" not in st.session_state:
        st.session_state.platform_paths = backend.default_paths()
    return st.session_state.platform_paths


def _df(rows: Any) -> pd.DataFrame:
    return pd.DataFrame(list(rows or ()))


def _metric_grid(metrics: dict[str, Any]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.markdown(
            f"""
            <div class="metric-tile">
              <div class="metric-label">{escape(str(label))}</div>
              <div class="metric-value">{escape(str(value))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _download_directory(label: str, path: Path, file_name: str) -> None:
    if path.exists():
        st.download_button(
            label,
            data=backend.zip_directory_bytes(path),
            file_name=file_name,
            mime="application/zip",
            width="stretch",
        )
    else:
        st.button(label, disabled=True, width="stretch")


def _download_file(label: str, path: Path, mime: str = "application/octet-stream") -> None:
    if path.exists():
        st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, width="stretch")
    else:
        st.button(label, disabled=True, width="stretch")


def _json_block(payload: Any) -> None:
    st.code(json.dumps(payload, indent=2, sort_keys=True, default=str), language="json")


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          --surface: #ffffff;
          --muted: #f6f8fa;
          --line: #d0d7de;
          --text: #1f2328;
          --subtle: #59636e;
          --accent: #0969da;
          --ok: #1a7f37;
          --warn: #9a6700;
          --bad: #cf222e;
        }
        .block-container {
          padding-top: 1.25rem;
          padding-bottom: 2rem;
          max-width: 1500px;
        }
        h1, h2, h3 {
          letter-spacing: 0;
        }
        div[data-testid="stMetric"], .metric-tile {
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 0.75rem 0.85rem;
          background: var(--surface);
        }
        .metric-tile {
          min-height: 92px;
        }
        .metric-label {
          color: var(--subtle);
          font-size: 0.875rem;
          line-height: 1.2;
          margin-bottom: 0.5rem;
        }
        .metric-value {
          color: var(--text);
          font-size: 1.65rem;
          font-weight: 650;
          line-height: 1.1;
          overflow-wrap: anywhere;
        }
        div[data-testid="stMetric"] * {
          color: var(--text) !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"],
        div[data-testid="stMetric"] [data-testid="stMetricValue"],
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
          color: var(--text) !important;
          opacity: 1 !important;
        }
        div[data-testid="stMetric"] label {
          color: var(--subtle);
        }
        section[data-testid="stSidebar"] {
          border-right: 1px solid var(--line);
        }
        .status-row {
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 0.75rem 0.9rem;
          background: var(--muted);
          margin-bottom: 0.75rem;
        }
        .small-muted {
          color: var(--subtle);
          font-size: 0.875rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_shell() -> str:
    paths = _paths()
    st.sidebar.title("Agentic CFO")
    st.sidebar.caption("Experiment operations")
    nav = st.sidebar.radio("Navigate", NAV_ITEMS, label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Workspace")
    st.sidebar.text(str(paths.repo_root))
    st.sidebar.button("Refresh", width="stretch")
    return nav


def render_dashboard(paths: backend.PlatformPaths) -> None:
    health = backend.project_health(paths)
    dataset = backend.dataset_status(paths.dataset_dir)
    results = backend.result_status(paths.results_dir)

    st.title("Agentic CFO Operations")
    st.caption("Manage datasets, experiments, run artifacts, audit evidence, and dissertation result outputs from one Python-backed UI.")
    _metric_grid(
        {
            "Dataset Ready": "Yes" if health["dataset_ready"] else "No",
            "Result Rows": health["result_rows"],
            "Runs": health["run_count"],
            "Configs": health["config_count"],
        }
    )

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Dataset")
        st.markdown(
            f"""
            <div class="status-row">
              <b>Location</b><br><span class="small-muted">{dataset["dataset_dir"]}</span><br>
              <b>Cases</b>: {dataset["case_count"]} &nbsp; <b>Trial balance rows</b>: {dataset["trial_balance_rows"]}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if dataset["manifest"]:
            st.json(dataset["manifest"].get("validation", {}))
    with right:
        st.subheader("Results")
        st.markdown(
            f"""
            <div class="status-row">
              <b>Location</b><br><span class="small-muted">{results["results_dir"]}</span><br>
              <b>Systems</b>: {len(results["systems"])} &nbsp; <b>Conditions</b>: {len(results["conditions"])}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if results["systems"]:
            st.write(", ".join(results["systems"]))

    st.subheader("Next Useful GUI Work")
    st.write(
        "Add authentication/RBAC, background job workers, live logs, persisted job history, reviewer imports, "
        "statistical notebooks, external metric adapters, and deployment-grade storage once the local platform flow is stable."
    )


def render_experiments(paths: backend.PlatformPaths) -> None:
    st.title("Experiments")
    configs = backend.list_configs(paths.repo_root)
    contract_options = configs["experiments"] or (paths.repo_root / "configs" / "experiment" / "paper_v1.yaml",)
    dataset_options = configs["datasets"] or (paths.repo_root / "configs" / "datasets" / "paper_synthetic_v1.yaml",)

    left, right = st.columns([0.42, 0.58])
    with left:
        st.subheader("Controls")
        contract_path = st.selectbox("Experiment contract", contract_options, format_func=lambda p: str(p.relative_to(paths.repo_root)))
        dataset_config = st.selectbox("Dataset config", dataset_options, format_func=lambda p: str(p.relative_to(paths.repo_root)))
        max_cases = st.number_input("Max cases per condition", min_value=1, max_value=10000, value=2, step=1)
        full_run = st.checkbox("Run all generated cases", value=False)
        st.caption("Operations call Python backend functions directly. No experiment action shells out through the CLI.")

        if st.button("Generate Dataset", width="stretch"):
            with st.spinner("Generating dataset"):
                st.session_state.last_dataset_status = backend.generate_dataset_from_config(
                    config_path=Path(dataset_config),
                    out_dir=paths.dataset_dir,
                )
            st.success("Dataset generated")

        if st.button("Run Experiment Matrix", type="primary", width="stretch"):
            with st.spinner("Running matrix"):
                st.session_state.last_experiment_status = backend.run_experiment_matrix_backend(
                    contract_path=Path(contract_path),
                    dataset_out=paths.dataset_dir,
                    results_out=paths.results_dir,
                    max_cases_per_condition=None if full_run else int(max_cases),
                )
            st.success("Experiment matrix complete")

        if st.button("Regenerate Chapter 4 Tables", width="stretch"):
            with st.spinner("Writing tables"):
                st.session_state.last_tables = backend.regenerate_chapter4_tables_backend(results_dir=paths.results_dir)
            st.success("Tables written")

    with right:
        st.subheader("Contract Preview")
        if Path(contract_path).exists():
            _json_block(backend.load_yaml_mapping(Path(contract_path)))
        st.subheader("Last Operation")
        _json_block(st.session_state.get("last_experiment_status") or st.session_state.get("last_dataset_status") or {})


def render_runs(paths: backend.PlatformPaths) -> None:
    st.title("Runs")
    left, right = st.columns([0.36, 0.64])
    with left:
        st.subheader("Create Fixture Run")
        requested_run_id = st.text_input("Run ID", value="")
        if st.button("Run Agentic CFO Fixture", type="primary", width="stretch"):
            with st.spinner("Running fixture"):
                st.session_state.last_fixture_run = backend.run_fixture_backend(
                    fixture_dir=paths.fixture_dir,
                    runs_dir=paths.runs_dir,
                    run_id=requested_run_id.strip() or None,
                    create_fixture=True,
                )
            st.success("Fixture run complete")
        if st.session_state.get("last_fixture_run"):
            _json_block(st.session_state.last_fixture_run)

        st.subheader("Run Inventory")
        run_roots = backend.list_run_roots(paths.runs_dir)
        selected = st.selectbox("Run", run_roots, format_func=lambda p: p.name) if run_roots else None
        if selected:
            _download_directory("Download Run Bundle", selected, f"{selected.name}.zip")

    with right:
        st.subheader("Run Detail")
        if not backend.list_run_roots(paths.runs_dir):
            st.info("No runs found yet.")
            return
        selected = selected or backend.list_run_roots(paths.runs_dir)[0]
        detail = backend.run_detail(selected)
        cols = st.columns(3)
        cols[0].metric("Audit Valid", "Yes" if detail["audit_valid"] else "No")
        cols[1].metric("Bundle Valid", "Yes" if detail["artifact_bundle_valid"] else "No")
        cols[2].metric("Events", len(detail["audit_events"]))
        st.dataframe(_df([{"event_type": k, "count": v} for k, v in detail["audit_lifecycle"].items()]), width="stretch", hide_index=True)
        tabs = st.tabs(["Manifest", "Report", "Verification", "Release", "Files"])
        for tab, name in zip(tabs[:4], ("manifest", "report", "verification", "release")):
            with tab:
                _json_block(detail.get(name, {}))
        with tabs[4]:
            st.write(detail["files"])


def render_results(paths: backend.PlatformPaths) -> None:
    st.title("Results")
    rows = backend.load_results(paths.results_dir)
    status = backend.result_status(paths.results_dir)
    if not rows:
        st.info("No result rows found. Run the experiment matrix first.")
        return

    _metric_grid({"Rows": len(rows), "Systems": len(status["systems"]), "Conditions": len(status["conditions"])})
    filters = st.columns(3)
    system_filter = filters[0].multiselect("Systems", status["systems"], default=status["systems"])
    condition_filter = filters[1].multiselect("Conditions", status["conditions"], default=status["conditions"])
    audit_only = filters[2].checkbox("Human-audit eligible only", value=False)
    filtered = [
        row
        for row in rows
        if row["system"] in system_filter
        and row["condition"] in condition_filter
        and (not audit_only or bool(row.get("human_audit_eligible")))
    ]

    st.subheader("Result Rows")
    st.dataframe(_df(filtered), width="stretch", hide_index=True)
    st.subheader("System and Condition Summary")
    st.dataframe(_df(backend.system_condition_summary(paths.results_dir)), width="stretch", hide_index=True)
    st.subheader("Perturbation Deltas")
    st.dataframe(_df(backend.perturbation_delta_summary(paths.results_dir)), width="stretch", hide_index=True)

    d1, d2, d3 = st.columns(3)
    with d1:
        _download_file("Download Results JSON", paths.results_dir / "results.json", "application/json")
    with d2:
        _download_file("Download Summary CSV", paths.results_dir / "table_system_condition_summary.csv", "text/csv")
    with d3:
        _download_file("Download Deltas CSV", paths.results_dir / "table_perturbation_deltas.csv", "text/csv")


def render_data(paths: backend.PlatformPaths) -> None:
    st.title("Data")
    status = backend.dataset_status(paths.dataset_dir)
    _metric_grid({"Dataset Ready": "Yes" if status["exists"] else "No", "Cases": status["case_count"], "Rows": status["trial_balance_rows"]})

    left, right = st.columns([0.45, 0.55])
    with left:
        st.subheader("Manifest")
        _json_block(status["manifest"])
        _download_directory("Download Dataset Zip", paths.dataset_dir, "paper_synthetic_v1_dataset.zip")
    with right:
        st.subheader("Cases")
        cases_path = paths.dataset_dir / "cases.jsonl"
        if cases_path.exists():
            cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            st.dataframe(_df(cases), width="stretch", hide_index=True)
        st.subheader("Trial Balance")
        st.dataframe(_df(backend.read_csv_rows(paths.dataset_dir / "trial_balance.csv")), width="stretch", hide_index=True)


def render_audit(paths: backend.PlatformPaths) -> None:
    st.title("Audit")
    run_roots = backend.list_run_roots(paths.runs_dir)
    if not run_roots:
        st.info("No run audit bundles found.")
        return
    selected = st.selectbox("Run", run_roots, format_func=lambda p: p.name)
    detail = backend.run_detail(selected)
    _metric_grid(
        {
            "Audit Valid": "Yes" if detail["audit_valid"] else "No",
            "Bundle Valid": "Yes" if detail["artifact_bundle_valid"] else "No",
            "Events": len(detail["audit_events"]),
        }
    )
    st.subheader("Lifecycle")
    st.dataframe(_df([{"event_type": k, "count": v} for k, v in detail["audit_lifecycle"].items()]), width="stretch", hide_index=True)
    st.subheader("Events")
    st.dataframe(_df(detail["audit_events"]), width="stretch", hide_index=True)
    st.subheader("Checksums")
    _json_block(detail.get("checksums", {}))


def render_human_audit(paths: backend.PlatformPaths) -> None:
    st.title("Human Audit")
    st.caption("Validate sampling and agreement mechanics. Actual CPA ratings should be imported as separate controlled artifacts.")
    per_system = st.number_input("Sample per system", min_value=1, max_value=120, value=10, step=1)
    out_path = paths.human_audit_dir / "demo_summary.json"
    if st.button("Run Human Audit Demo", type="primary", width="stretch"):
        with st.spinner("Computing blinded sample and agreement"):
            st.session_state.human_audit_summary = backend.human_audit_demo_backend(
                results_dir=paths.results_dir,
                out_path=out_path,
                per_system=int(per_system),
            )
        st.success("Human audit workflow check complete")

    summary = st.session_state.get("human_audit_summary")
    if summary is None and out_path.exists():
        summary = backend.read_json(out_path)
    if summary:
        _metric_grid(
            {
                "Sample": summary["sample_count"],
                "Ratings": summary["rating_count"],
                "Raw Agreement": f'{summary["raw_agreement"]:.3f}',
                "Weighted Kappa": f'{summary["weighted_cohens_kappa"]:.3f}',
            }
        )
        st.subheader("Adjudicated Distribution")
        st.dataframe(_df([{"rating": k, "count": v} for k, v in summary["adjudicated_distribution"].items()]), width="stretch", hide_index=True)
        _download_file("Download Human Audit Summary", out_path, "application/json")


def render_settings(paths: backend.PlatformPaths) -> None:
    st.title("Settings")
    st.subheader("Configured Paths")
    st.dataframe(_df([{"key": k, "path": v} for k, v in paths.to_dict().items()]), width="stretch", hide_index=True)

    st.subheader("Configuration Files")
    configs = backend.list_configs(paths.repo_root)
    rows = []
    for group, files in configs.items():
        for file in files:
            rows.append({"group": group, "file": str(file.relative_to(paths.repo_root))})
    st.dataframe(_df(rows), width="stretch", hide_index=True)

    selected = st.selectbox("Preview config", [file for files in configs.values() for file in files], format_func=lambda p: str(p.relative_to(paths.repo_root)))
    if selected:
        _json_block(backend.load_yaml_mapping(Path(selected)))


def render_gui_plan() -> None:
    st.title("GUI Plan")
    st.write("The implemented UI now covers local project operations. The next GUI plan should include:")
    plan_rows = (
        {"area": "Access control", "work": "Add authentication, project roles, and RBAC for Preparer, Reviewer, Approver, and Admin."},
        {"area": "Background jobs", "work": "Move long experiment runs to a job queue with cancellation, retry, progress, and log streaming."},
        {"area": "Persistent state", "work": "Replace folder scans with a SQLite/Postgres metadata store for datasets, runs, artifacts, reviewers, and jobs."},
        {"area": "Reviewer workflow", "work": "Add CPA rating import, double-blind assignment, adjudication queue, comments, rubric locks, and exportable reviewer packets."},
        {"area": "Prompt governance", "work": "Add prompt template versioning, diff review, approval gates, and provider/runtime capture."},
        {"area": "Metric adapters", "work": "Add external FActScore/RAGAS integrations with cached scoring payloads and evaluator version manifests."},
        {"area": "Analytics", "work": "Add hypothesis views, confidence intervals, exact Chapter 4 tables, charts, and statistical notebook exports."},
        {"area": "Artifact registry", "work": "Add searchable evidence spans, claims, exceptions, release attestations, and signed checksum manifests."},
        {"area": "Operations", "work": "Add alerts for failed thresholds, stale datasets, broken audit chains, missing artifacts, and incomplete human-audit samples."},
        {"area": "Deployment", "work": "Package the UI as a service with environment profiles, health checks, backups, and object-store support."},
    )
    st.dataframe(_df(plan_rows), width="stretch", hide_index=True)


def app() -> None:
    _require_streamlit()
    st.set_page_config(page_title="Agentic CFO Platform", page_icon=None, layout="wide", initial_sidebar_state="expanded")
    _apply_theme()
    paths = _paths()
    nav = render_shell()
    if nav == "Dashboard":
        render_dashboard(paths)
    elif nav == "Experiments":
        render_experiments(paths)
    elif nav == "Runs":
        render_runs(paths)
    elif nav == "Results":
        render_results(paths)
    elif nav == "Data":
        render_data(paths)
    elif nav == "Audit":
        render_audit(paths)
    elif nav == "Human Audit":
        render_human_audit(paths)
    elif nav == "Settings":
        render_settings(paths)
    else:
        render_gui_plan()


def main() -> int:
    if "streamlit" not in sys.modules:
        print('Run this app with: streamlit run praxis_gui.py')
        return 0
    app()
    return 0


if __name__ == "__main__":
    app()
