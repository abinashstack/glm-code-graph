#!/usr/bin/env python3
"""Verification for blast_radius -- run: python test_blast_radius.py"""

import importlib.util
import shutil
import tempfile
from pathlib import Path

from blast_radius import build_graph, select

ROOT = Path(__file__).parent


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def test_ast_finds_function_local_import():
    # auth.py has `from config import SECRET_KEY` *inside* a method. A line-prefix
    # scan of the module's leading lines would miss it; the AST does not.
    graph = build_graph(ROOT)
    assert "config.py" in graph.modules["auth.py"].imports


def test_change_to_config_pulls_its_importer():
    sel = select(ROOT, ["config.py"])
    assert "auth.py" in sel.files
    assert sel.reason["auth.py"].startswith("imports the change")


def test_unrelated_change_stays_narrow():
    # nothing imports user.py or database.py, so their radius is just themselves.
    for changed in ("user.py", "database.py"):
        sel = select(ROOT, [changed])
        assert sel.files == [changed], (changed, sel.files)


def test_forward_dependency_is_context_not_impact():
    sel = select(ROOT, ["auth.py"])
    assert sel.reason["auth.py"] == "changed"
    assert sel.reason["config.py"] == "dependency of the change"


def test_token_budget_trims_but_keeps_changed_file():
    sel = select(ROOT, ["config.py"], token_budget=1)
    assert sel.files == ["config.py"]
    assert "auth.py" in sel.dropped


def test_reduction_is_reported():
    sel = select(ROOT, ["user.py"])
    assert 0 < sel.token_reduction < 100


def test_budget_trim_is_a_priority_prefix():
    # x changed; a imports x (1 hop up, large); b imports a (2 hops up, small).
    # A budget that fits b but not a must still drop b -- keeping it would leave
    # the selection missing a higher-priority file (a) than one it kept (b).
    work = Path(tempfile.mkdtemp())
    try:
        (work / "x.py").write_text("VALUE = 1\n")
        (work / "a.py").write_text("import x\n" + "# pad\n" * 200)
        (work / "b.py").write_text("import a\n")
        sel = select(work, ["x.py"], token_budget=12)
        assert sel.files == ["x.py"], sel.files
        assert set(sel.dropped) == {"a.py", "b.py"}, sel.dropped
    finally:
        shutil.rmtree(work)


def test_relative_import_resolves_within_its_own_package():
    # `from . import utils` in pkg1/mod.py must resolve to pkg1/utils.py --
    # specifically, not by a repo-wide name search that would find pkg2's
    # same-named file instead (or refuse to resolve at all, ambiguously).
    work = Path(tempfile.mkdtemp())
    try:
        (work / "pkg1").mkdir()
        (work / "pkg2").mkdir()
        (work / "pkg1" / "utils.py").write_text("A = 1\n")
        (work / "pkg2" / "utils.py").write_text("B = 2\n")
        (work / "pkg1" / "mod.py").write_text("from . import utils\n")
        graph = build_graph(work)
        assert graph.modules["pkg1/mod.py"].imports == {"pkg1/utils.py"}
    finally:
        shutil.rmtree(work)


def test_skip_dirs_only_apply_inside_the_repo():
    # A SKIP_DIRS name (e.g. "build") appearing in an *ancestor* of the repo
    # root -- a common CI checkout layout -- must not exclude every file.
    outer = Path(tempfile.mkdtemp())
    try:
        work = outer / "build" / "myrepo"
        work.mkdir(parents=True)
        (work / "a.py").write_text("VALUE = 1\n")
        graph = build_graph(work)
        assert set(graph.modules) == {"a.py"}
    finally:
        shutil.rmtree(outer)


def test_duplicate_stems_across_directories_do_not_collide():
    # Nodes are keyed by repo-relative path, not filename stem: two `util.py`
    # files in different packages must both survive as distinct graph nodes.
    work = Path(tempfile.mkdtemp())
    try:
        (work / "pkg1").mkdir()
        (work / "pkg2").mkdir()
        (work / "pkg1" / "util.py").write_text("A = 1\n")
        (work / "pkg2" / "util.py").write_text("B = 2\n")
        graph = build_graph(work)
        assert set(graph.modules) == {"pkg1/util.py", "pkg2/util.py"}
    finally:
        shutil.rmtree(work)


def test_cache_reparses_only_changed_files():
    work = Path(tempfile.mkdtemp())
    try:
        (work / "a.py").write_text("VALUE = 1\n")
        g1 = build_graph(work)
        assert g1.stats == {"parsed": 1, "cached": 0}

        g2 = build_graph(work)
        assert g2.stats == {"parsed": 0, "cached": 1}

        (work / "a.py").write_text("VALUE = 2\n")
        g3 = build_graph(work)
        assert g3.stats == {"parsed": 1, "cached": 0}
    finally:
        shutil.rmtree(work)


def test_resolution_updates_even_when_parse_is_cached():
    # a.py's own parse is unchanged (cache hit) between builds, but resolving
    # its `from b import X` must still pick up b.py once b.py is added --
    # resolution is recomputed against the live file set on every build.
    work = Path(tempfile.mkdtemp())
    try:
        (work / "a.py").write_text("from b import X\n")
        g1 = build_graph(work)
        assert g1.modules["a.py"].imports == set()

        (work / "b.py").write_text("X = 1\n")
        g2 = build_graph(work)
        assert g2.stats["cached"] == 1   # a.py itself was not re-parsed
        assert g2.modules["a.py"].imports == {"b.py"}
    finally:
        shutil.rmtree(work)


def test_deeply_nested_js_does_not_blow_the_stack():
    if not _has("tree_sitter") or not _has("tree_sitter_javascript"):
        print("  skip test_deeply_nested_js_does_not_blow_the_stack (tree-sitter-javascript not installed)")
        return
    work = Path(tempfile.mkdtemp())
    try:
        nested = "[" * 3000 + "1" + "]" * 3000
        (work / "deep.js").write_text(f"import './x.js';\nconst a = {nested};\n")
        graph = build_graph(work, use_cache=False)   # must not raise RecursionError
        assert "deep.js" in graph.modules
    finally:
        shutil.rmtree(work)


def test_javascript_relative_import_resolves():
    if not _has("tree_sitter") or not _has("tree_sitter_javascript"):
        print("  skip test_javascript_relative_import_resolves (tree-sitter-javascript not installed)")
        return
    sel = select(ROOT, ["web/utils.js"])
    assert "web/app.js" in sel.files
    assert sel.reason["web/app.js"].startswith("imports the change")


def test_typescript_imports_a_js_file():
    if not _has("tree_sitter") or not _has("tree_sitter_typescript"):
        print("  skip test_typescript_imports_a_js_file (tree-sitter-typescript not installed)")
        return
    graph = build_graph(ROOT)
    assert "web/utils.js" in graph.modules["web/format.ts"].imports


def test_go_import_fans_out_to_the_importing_package():
    if not _has("tree_sitter") or not _has("tree_sitter_go"):
        print("  skip test_go_import_fans_out_to_the_importing_package (tree-sitter-go not installed)")
        return
    sel = select(ROOT, ["service/util/helper.go"])
    assert "service/handler.go" in sel.files
    assert sel.reason["service/handler.go"].startswith("imports the change")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
