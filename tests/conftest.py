import pytest

from editorial_engine.fixtures import generate_fixtures
from editorial_engine.pipeline import assemble_package
from editorial_engine.qc import run_qc, write_citation_report


@pytest.fixture
def sources(tmp_path):
    path = tmp_path / "sources"
    generate_fixtures(path)
    return path


@pytest.fixture
def package(tmp_path, sources):
    path = tmp_path / "package"
    assemble_package(sources, path)
    write_citation_report(path)
    result = run_qc(path)
    assert result["passed"]
    return path
