from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from agentic_cfo.ui import (
    analytics as analytics_backend,
    backend,
    reviews as reviews_backend,
    settings as settings_backend,
)
from agentic_cfo.ui.jobs import get_job_manager

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised only when UI extra is missing.
    st = None  # type: ignore[assignment]


NAV_ITEMS = (
    "Dashboard",
    "Experiments",
    "Jobs",
    "Runs",
    "Results",
    "Data",
    "Audit",
    "Human Audit",
    "Reviewer",
    "Analytics",
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


def _manager(paths: backend.PlatformPaths):
    # Process-level singleton: survives Streamlit reruns so background jobs keep
    # running and progress is read back from the SQLite store.
    return get_job_manager(paths)


def _status_badge(status: str) -> str:
    color = {
        "queued": "var(--subtle)",
        "running": "var(--accent)",
        "succeeded": "var(--ok)",
        "failed": "var(--bad)",
        "cancelled": "var(--warn)",
    }.get(status, "var(--subtle)")
    return f'<span style="color:{color};font-weight:600">{escape(status)}</span>'


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

    default_index = 0
    forced = st.session_state.pop("force_nav", None)
    if forced in NAV_ITEMS:
        default_index = NAV_ITEMS.index(forced)
    nav = st.sidebar.radio("Navigate", NAV_ITEMS, index=default_index, label_visibility="collapsed")

    active_jobs = [j for j in _manager(paths).store.list_jobs(limit=50) if not j.is_terminal]
    if active_jobs:
        st.sidebar.info(f"{len(active_jobs)} job(s) running")

    llm = settings_backend.current_settings(paths.repo_root / ".env")
    st.sidebar.caption(f"Mode: {llm['mode'].upper()} · {llm['model']}")

    st.sidebar.divider()
    st.sidebar.caption("Workspace")
    st.sidebar.text(str(paths.repo_root))
    if st.sidebar.button("Refresh", width="stretch"):
        st.rerun()
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

    st.subheader("Platform Status")
    st.write(
        "Implemented: background job queue with progress/cancel/logs, SQLite-persisted "
        "job history, and a Settings panel for the API key and deterministic/live mode. "
        "Remaining hardening is tracked on the GUI Plan page."
    )


def render_experiments(paths: backend.PlatformPaths) -> None:
    st.title("Experiments")
    manager = _manager(paths)
    configs = backend.list_configs(paths.repo_root)
    contract_options = configs["experiments"] or (paths.repo_root / "configs" / "experiment" / "paper_v1.yaml",)
    dataset_options = configs["datasets"] or (paths.repo_root / "configs" / "datasets" / "paper_synthetic_v1.yaml",)

    llm = settings_backend.current_settings(paths.repo_root / ".env")
    badge = "LIVE" if llm["mode"] == "live" else "DETERMINISTIC"
    if llm["mode"] == "live" and not llm["api_key_present"]:
        st.warning("Live mode is selected but no API key is set. Set it on the Settings page before running.")
    else:
        st.caption(f"Generation mode: **{badge}** · model: {llm['model']}")

    left, right = st.columns([0.42, 0.58])
    with left:
        st.subheader("Controls")
        contract_path = st.selectbox("Experiment contract", contract_options, format_func=lambda p: str(p.relative_to(paths.repo_root)))
        dataset_config = st.selectbox("Dataset config", dataset_options, format_func=lambda p: str(p.relative_to(paths.repo_root)))
        max_cases = st.number_input("Max cases per condition", min_value=1, max_value=10000, value=2, step=1)
        full_run = st.checkbox("Run all generated cases", value=False)
        st.caption("Operations run as background jobs. Track progress and cancel on the Jobs page.")

        if st.button("Generate Dataset", width="stretch"):
            job_id = manager.submit("generate_dataset", {"config_path": str(dataset_config)})
            st.session_state.last_job_id = job_id
            st.success(f"Queued dataset job · {job_id}")

        if st.button("Run Experiment Matrix", type="primary", width="stretch"):
            job_id = manager.submit(
                "run_experiment_matrix",
                {
                    "contract_path": str(contract_path),
                    "max_cases_per_condition": None if full_run else int(max_cases),
                },
            )
            st.session_state.last_job_id = job_id
            st.success(f"Queued experiment matrix · {job_id}")

        if st.button("Regenerate Chapter 4 Tables", width="stretch"):
            job_id = manager.submit("regenerate_tables", {})
            st.session_state.last_job_id = job_id
            st.success(f"Queued table regeneration · {job_id}")

    with right:
        st.subheader("Contract Preview")
        if Path(contract_path).exists():
            _json_block(backend.load_yaml_mapping(Path(contract_path)))
        last_job_id = st.session_state.get("last_job_id")
        if last_job_id:
            job = manager.store.get_job(last_job_id)
            if job:
                st.subheader("Most Recent Job")
                st.markdown(_status_badge(job.status), unsafe_allow_html=True)
                if not job.is_terminal:
                    st.progress(job.fraction, text=f"{job.progress}/{job.total}")
                    if st.button("Open Jobs page"):
                        st.session_state.force_nav = "Jobs"
                        st.rerun()
                else:
                    _json_block(job.to_dict())


def render_jobs(paths: backend.PlatformPaths) -> None:
    st.title("Jobs")
    manager = _manager(paths)
    jobs = manager.store.list_jobs(limit=100)
    active = [j for j in jobs if not j.is_terminal]

    top = st.columns([0.25, 0.25, 0.5])
    top[0].metric("Active", len(active))
    top[1].metric("Total", len(jobs))
    with top[2]:
        c1, c2 = st.columns(2)
        if c1.button("Refresh", width="stretch"):
            st.rerun()
        if c2.button("Clear finished", width="stretch"):
            manager.store.clear_terminal_jobs()
            st.rerun()
    auto = st.checkbox("Auto-refresh while jobs are running", value=bool(active))

    if not jobs:
        st.info("No jobs yet. Start one from the Experiments, Runs, or Human Audit pages.")
        return

    for job in jobs:
        with st.container(border=True):
            head = st.columns([0.5, 0.3, 0.2])
            head[0].markdown(f"**{escape(job.kind)}** · `{escape(job.id)}`")
            head[1].markdown(_status_badge(job.status), unsafe_allow_html=True)
            if not job.is_terminal:
                if head[2].button("Cancel", key=f"cancel_{job.id}", width="stretch"):
                    manager.cancel(job.id)
                    st.toast(f"Cancellation requested for {job.id}")
            if not job.is_terminal:
                st.progress(job.fraction, text=f"{job.progress}/{job.total} · {job.message}")
            elif job.status == "failed":
                st.error(job.error or "failed")
            with st.expander("Details", expanded=not job.is_terminal):
                if job.params:
                    st.caption("Params")
                    _json_block(job.params)
                if job.result:
                    st.caption("Result")
                    _json_block(job.result)
                log = manager.read_log(job.id, tail=200)
                if log:
                    st.caption("Log (tail)")
                    st.code(log, language="text")

    if auto and active:
        import time as _time

        _time.sleep(1.5)
        st.rerun()


def render_runs(paths: backend.PlatformPaths) -> None:
    st.title("Runs")
    left, right = st.columns([0.36, 0.64])
    with left:
        st.subheader("Create Fixture Run")
        requested_run_id = st.text_input("Run ID", value="")
        if st.button("Run Agentic CFO Fixture", type="primary", width="stretch"):
            job_id = _manager(paths).submit("fixture_run", {"run_id": requested_run_id.strip() or None})
            st.session_state.last_job_id = job_id
            st.success(f"Queued fixture run · {job_id} (track on Jobs page)")

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

    meta = backend.read_json(paths.results_dir / "results.json").get("meta", {}) if (paths.results_dir / "results.json").exists() else {}
    if meta:
        mode = str(meta.get("llm_mode", "?")).upper()
        st.caption(
            f"Provenance · mode: **{mode}** · model: {meta.get('llm_model', '?')} · "
            f"replications: {meta.get('replications', '?')} · rows: {meta.get('row_count', len(rows))}"
        )

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
        job_id = _manager(paths).submit("human_audit_demo", {"per_system": int(per_system)})
        st.session_state.last_job_id = job_id
        st.success(f"Queued human-audit demo · {job_id} (track on Jobs page)")

    summary = None
    if out_path.exists():
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


def render_reviewer(paths: backend.PlatformPaths) -> None:
    st.title("Reviewer")
    store = _manager(paths).store
    results_dir = paths.results_dir
    artifacts = reviews_backend.load_artifacts(results_dir)
    if not artifacts:
        st.info(
            "No retained artifacts found. Run the experiment matrix on the Experiments "
            "page (it now persists artifacts to results/artifacts.jsonl), then return here."
        )
        return

    with st.expander("Review flags — CPA four-level rubric", expanded=False):
        st.dataframe(_df(reviews_backend.rubric_flags()), hide_index=True, width="stretch")

    top = st.columns([0.4, 0.3, 0.3])
    reviewer_id = top[0].text_input("Reviewer ID", value=st.session_state.get("reviewer_id", "reviewer:1"))
    st.session_state.reviewer_id = reviewer_id
    per_system = top[1].number_input("Sample per system", min_value=1, max_value=200, value=5, step=1)
    if top[2].button("Assign blinded sample", width="stretch"):
        n = reviews_backend.assign_blinded_sample(store, results_dir=results_dir, per_system=int(per_system))
        st.success(f"Assigned {n} blinded items")
        st.rerun()

    samples = store.list_review_samples()
    if not samples:
        st.info("No blinded sample assigned yet. Choose a size and click Assign blinded sample.")
        return

    prog = reviews_backend.reviewer_progress(store, reviewer_id)
    st.progress(prog["fraction"], text=f"{reviewer_id}: {prog['reviewed']}/{prog['total']} reviewed")

    options = [s["blinded_id"] for s in samples]
    nxt = reviews_backend.next_unrated(store, reviewer_id)
    default_idx = options.index(nxt["blinded_id"]) if nxt else 0

    def _fmt(b: str) -> str:
        done = store.get_review(blinded_id=b, reviewer_id=reviewer_id)
        return f"{b}  {'✓' if done else '•'}"

    blinded_id = st.selectbox("Item", options, index=default_idx, format_func=_fmt)
    item = reviews_backend.reviewable_item(store, artifacts, blinded_id=blinded_id, reviewer_id=reviewer_id)
    if item is None:
        st.warning("Item not found.")
        return

    left, right = st.columns([0.58, 0.42])
    with left:
        st.subheader("Artifact (blinded)")
        st.caption(
            f"Condition: **{item['condition']}** · release action: {item['release_action']} · "
            f"verification: {item['verification_status']}"
        )
        st.markdown(f"> {escape(item['narrative'])}")
        st.caption("Claims")
        claim_rows = [
            {
                "claim": c.get("text"),
                "type": c.get("claim_type"),
                "value": c.get("value"),
                "evidence_spans": len(c.get("evidence", [])),
            }
            for c in item["claims"]
        ]
        st.dataframe(_df(claim_rows), hide_index=True, width="stretch")
        st.caption("Source trial balance")
        st.dataframe(_df(item["source_records"]), hide_index=True, width="stretch")

    with right:
        st.subheader("Metrics")
        st.dataframe(
            _df([{"metric": k, "value": round(float(v), 3)} for k, v in item["metrics"].items()]),
            hide_index=True,
            width="stretch",
        )
        st.subheader("Classification")
        flags = reviews_backend.rubric_flags()
        ratings = [f["rating"] for f in flags]
        labels = {f["rating"]: f"{f['rating']} — {f['label']}" for f in flags}
        default_rating = item["existing_rating"] if item["existing_rating"] is not None else 3
        rating = st.radio(
            "Review flag",
            ratings,
            index=ratings.index(default_rating),
            format_func=lambda r: labels[r],
            help="\n".join(f"{f['rating']} = {f['definition']}" for f in flags),
        )
        rationale = st.text_area("Rationale (optional)", value=item["existing_rationale"])
        if st.button("Save rating", type="primary", width="stretch"):
            reviews_backend.record_review(
                store,
                blinded_id=blinded_id,
                artifact_id=item["artifact_id"],
                reviewer_id=reviewer_id,
                rating=int(rating),
                rationale=rationale,
            )
            st.success("Rating saved")
            st.rerun()


def render_analytics(paths: backend.PlatformPaths) -> None:
    st.title("Analytics")
    store = _manager(paths).store
    if not reviews_backend.load_results_rows(paths.results_dir):
        st.info("No results yet. Run the experiment matrix first.")
        return

    data = analytics_backend.full_analytics(
        dataset_dir=paths.dataset_dir, results_dir=paths.results_dir, store=store
    )
    syn, arts, mets, rev = data["synthetic_data"], data["artifacts"], data["metrics"], data["reviews"]

    st.subheader("Synthetic Data")
    _metric_grid({
        "Cases": syn["case_count"],
        "Accounts": len(syn["accounts"]),
        "TB Rows": syn["trial_balance_rows"],
        "Seed": syn.get("seed") if syn.get("seed") is not None else "—",
    })
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Cases per partition")
        st.bar_chart(pd.Series(syn["partitions"], name="cases"))
    with c2:
        st.caption("Account balance ranges")
        st.dataframe(
            _df([{"account": a, **v} for a, v in syn["account_stats"].items()]),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Artifacts")
    _metric_grid({
        "Retained": arts["retained_artifacts"],
        "Result Rows": arts["total_rows"],
        "Mode": (arts["llm_mode"] or "?").upper(),
        "Audit-eligible": arts["human_audit_eligible"],
    })
    if arts["artifacts_sha256"]:
        st.caption(f"Tamper-evident digest (sha256): `{arts['artifacts_sha256'][:48]}…`")
    a1, a2 = st.columns(2)
    with a1:
        st.caption("Release actions")
        st.bar_chart(pd.Series(arts["release_actions"], name="count"))
    with a2:
        st.caption("Artifacts by system × condition")
        st.dataframe(_df(arts["by_system_condition"]), hide_index=True, width="stretch")

    st.subheader("Metrics across baselines and agentic CFO")
    clean = mets["clean_metric_by_system"]
    if clean:
        st.caption("Clean-condition metric profile by system")
        st.bar_chart(pd.DataFrame(clean))
    st.caption("System × condition summary")
    st.dataframe(_df(mets["summary"]), hide_index=True, width="stretch")
    st.caption("Release-gate pass rate by system × condition")
    st.dataframe(_df(mets["gate_pass_by_system_condition"]), hide_index=True, width="stretch")
    st.caption("Perturbation degradation (deltas vs clean)")
    st.dataframe(_df(mets["deltas"]), hide_index=True, width="stretch")

    st.subheader("Reviewer Progress & Ratings")
    _metric_grid({
        "Reviews": rev["review_count"],
        "Reviewers": rev["reviewer_count"],
        "Raw Agreement": f'{rev["raw_agreement"]:.3f}',
        "Weighted κ": f'{rev["weighted_cohens_kappa"]:.3f}',
    })
    if rev["review_count"]:
        r1, r2 = st.columns(2)
        with r1:
            st.caption("Rating distribution (all reviewers)")
            st.bar_chart(pd.Series(rev["rating_distribution"], name="count"))
            st.caption("Reviews per reviewer")
            st.dataframe(
                _df([{"reviewer": k, "reviews": v} for k, v in rev["ratings_per_reviewer"].items()]),
                hide_index=True,
                width="stretch",
            )
        with r2:
            st.caption("Mean rating by true system (reveal)")
            st.bar_chart(pd.Series(rev["mean_rating_by_system"], name="mean_rating"))
            st.caption("Adjudicated distribution")
            st.dataframe(
                _df([{"rating": k, "count": v} for k, v in rev["adjudicated_distribution"].items()]),
                hide_index=True,
                width="stretch",
            )
    else:
        st.info("No reviews recorded yet — classify artifacts on the Reviewer page.")


def render_settings(paths: backend.PlatformPaths) -> None:
    st.title("Settings")

    env_path = paths.repo_root / ".env"
    current = settings_backend.current_settings(env_path)

    st.subheader("Model / Generation")
    grid = st.columns(3)
    grid[0].metric("Mode", current["mode"].upper())
    grid[1].metric("Model", current["model"])
    grid[2].metric("API key", current["api_key_masked"])
    if current["mode"] == "live" and not current["api_key_present"]:
        st.warning("Live mode requires an API key. Add one below to enable real model calls.")

    with st.form("llm_settings"):
        mode = st.radio(
            "Generation mode",
            settings_backend.MODES,
            index=settings_backend.MODES.index(current["mode"]),
            format_func=lambda m: "Deterministic (offline, reproducible)" if m == "deterministic" else "Live (OpenAI)",
            horizontal=True,
        )
        model = st.text_input("Model", value=current["model"])
        new_key = st.text_input(
            "OpenAI API key",
            value="",
            type="password",
            placeholder="leave blank to keep current key",
        )
        clear_key = st.checkbox("Clear stored API key", value=False)
        submitted = st.form_submit_button("Save settings", type="primary")
        if submitted:
            api_key_arg = "" if clear_key else (new_key or None)
            result = settings_backend.apply_settings(
                env_path=env_path,
                mode=mode,
                model=model,
                api_key=api_key_arg,
                persist=True,
            )
            st.success(f"Saved. Mode: {result['mode'].upper()} · key {result['api_key_masked']}")
            st.caption(f"Persisted to {result['env_path']} (gitignored). New jobs use these settings.")
            st.rerun()

    st.caption(
        "Deterministic mode runs offline and is fully reproducible. Live mode routes "
        "baseline B/C and the agentic system through the OpenAI API; cycle times then "
        "reflect measured latency."
    )

    st.divider()
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
    st.write("Implemented in this build:")
    done_rows = (
        {"area": "Background jobs", "status": "done", "detail": "Threaded job queue with progress, cooperative cancellation, and per-job logs."},
        {"area": "Persistent state", "status": "done", "detail": "SQLite store for job history, settings, review samples, and ratings (.agentic_cfo/platform.db)."},
        {"area": "Settings / LLM", "status": "done", "detail": "API-key field and deterministic/live mode toggle, persisted to .env and applied to running jobs."},
        {"area": "Artifact retention", "status": "done", "detail": "Matrix run persists every artifact (narrative/claims/evidence/source) to a content-hashed artifacts.jsonl."},
        {"area": "Reviewer workflow", "status": "done", "detail": "Blinded assignment, four-level rubric classification, progress tracking, agreement (raw + weighted kappa) and adjudication."},
        {"area": "Analytics", "status": "done", "detail": "Synthetic-data, artifact, cross-system metric, and reviewer progress/ratings summaries with charts."},
        {"area": "Provenance", "status": "done", "detail": "Results/Analytics surface llm_mode/model/replications and the artifact digest from results.json meta."},
    )
    st.dataframe(_df(done_rows), width="stretch", hide_index=True)

    st.write("Remaining hardening (not in scope for this build):")
    plan_rows = (
        {"area": "Prompt governance", "work": "Prompt template versioning, diff review, approval gates, and provider/runtime capture."},
        {"area": "Metric adapters", "work": "External FActScore/RAGAS integrations with cached scoring payloads and evaluator version manifests."},
        {"area": "Operations", "work": "Alerts for failed thresholds, stale datasets, broken audit chains, missing artifacts, and incomplete reviewer samples."},
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
    elif nav == "Jobs":
        render_jobs(paths)
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
    elif nav == "Reviewer":
        render_reviewer(paths)
    elif nav == "Analytics":
        render_analytics(paths)
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
