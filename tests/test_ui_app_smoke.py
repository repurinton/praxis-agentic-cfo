from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from agentic_cfo.ui import jobs as jobs_mod  # noqa: E402
from agentic_cfo.ui.platform import NAV_ITEMS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _reset_singleton():
    jobs_mod.reset_job_manager()
    yield
    jobs_mod.reset_job_manager()


def test_all_platform_pages_render_without_exception():
    at = AppTest.from_file(str(ROOT / "praxis_gui.py"), default_timeout=60)
    at.run()
    assert not at.exception, f"initial render raised: {at.exception}"

    for page in NAV_ITEMS:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, f"page {page!r} raised: {at.exception}"
