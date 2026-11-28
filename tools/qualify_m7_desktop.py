"""Drive the real desktop and its worker on pinned synthetic Lab photographs."""
import argparse
import json
import os
from pathlib import Path
from time import perf_counter, sleep
from urllib.request import urlopen
from zipfile import ZipFile

from PIL import Image
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from human3d.empirical_desktop import EmpiricalWindow, configured_engines
from human3d.reconstruction import BASELINE, sha_file
from verify_runtime_assets import peak_process_rss_bytes

FIXTURE_COMMIT = "115cb647b63f0ff289caa221b897780a5d521920"
FIXTURES = {
    "front.jpg": "ca0d99704731c0ec704887c3c109d3291e1940ba159788e2e78757f551149aa5",
    "side.jpg": "01949cf731cce513065ade86b92a19048d12ac3083543d6b285e6195588897d5",
    "threequarter.jpg": "136e10c85ea3d829ffb886ba7eca2f06ab94b347842fc214daea81003eaa9b32",
}


def fixtures(directory):
    directory.mkdir()
    root = ("https://raw.githubusercontent.com/egenovese-de/Human3D-2.0/"
            + FIXTURE_COMMIT + "/lab/fixtures/x-vlm/")
    for name, digest in FIXTURES.items():
        path = directory / name
        with urlopen(root + name, timeout=45) as response:
            path.write_bytes(response.read(1024 * 1024))
        if sha_file(path) != digest:
            raise ValueError(f"Fixture integrity failure: {name}")
        # The admitted source is a four-subject contact sheet. Use subject 04
        # across every view and remove the panel labels.
        with Image.open(path) as sheet:
            if sheet.size != (920, 470):
                raise ValueError(f"Unexpected contact sheet size: {name}")
            frame = sheet.crop((694, 2, 920, 442))
        path.unlink()
        frame.save(path.with_suffix(".png"))
    Image.new("RGB", (400, 500), "white").save(directory / "blank.png")


def qualify(assets, output, revision, *, geometry=False):
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "work"
    runtime.mkdir()
    photos = runtime / "fixtures"
    fixtures(photos)
    screenshots = output / "screenshots"
    screenshots.mkdir()
    started = perf_counter()
    app = QApplication([])
    settings = QSettings(str(runtime / "qualification.ini"), QSettings.Format.IniFormat)
    engines = configured_engines(assets)
    if geometry and "geometry" not in engines:
        raise RuntimeError("Engine B qualification requires its verified native asset registry.")
    window = EmpiricalWindow(engines, revision, settings=settings, reopen=False)
    window.show()
    QTest.qWaitForWindowExposed(window, 5000)
    app.processEvents()
    startup = perf_counter() - started
    profile = {"qt_platform": app.platformName(), "startup_seconds_to_show": startup,
               "fixture_commit": FIXTURE_COMMIT, "attempts": []}
    stages_seen = []

    def shot(name):
        app.processEvents()
        if not window.grab().save(str(screenshots / f"{name}.png")):
            raise RuntimeError(f"Could not capture {name}")

    def click_target(index):
        rect = window.photos.visualItemRect(window.photos.item(index))
        QTest.mouseClick(window.photos.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())

    def attempt(label, *, cancel=False, first=False, expect="complete"):
        start = perf_counter()
        window.actions["Generate 3D"].trigger()
        assert window.worker is not None
        window.worker.progress.connect(lambda event: stages_seen.append(event.stage))
        if cancel:
            window.actions["Cancel"].trigger()
            assert "Cancellation pending" in window.status.text()
        while window.worker is not None:
            app.processEvents()
            sleep(.025)
            if first and not (screenshots / "04-reconstructing.png").exists() and stages_seen:
                shot("04-reconstructing")
            if perf_counter() - start > 600:
                window.cancel()
                raise RuntimeError(f"Timed out: {label}")
        record = window.service.results(include_failures=True)[0]
        assert record.metadata["status"] == expect, record.metadata
        assert not list(window.service.attempts.glob(".attempt-*"))
        profile["attempts"].append({"scenario": label, "wall_seconds": perf_counter() - start,
                                    "peak_process_rss_bytes": peak_process_rss_bytes(),
                                    "project_bytes": sum(p.stat().st_size for p in (runtime / "project").rglob("*") if p.is_file()),
                                    "metadata": record.metadata})
        print(f"{label}: {record.metadata['status']} in {perf_counter() - start:.2f} s", flush=True)
        return record

    shot("01-initial")
    window.attach(runtime / "project", create=True)
    start = perf_counter()
    window.ingest([photos / "front.png"])
    profile["single_import_seconds"] = perf_counter() - start
    assert window.photos.count() == 1 and "TARGET" in window.photos.currentItem().text()
    shot("02-imported")
    single = attempt("A single frontal", first=True)
    assert window.active_result.id == single.id and window.canvas is not None
    shot("05-preview")
    window.pose.setCurrentIndex(0)
    window.orbit.setCurrentIndex(3)
    shot("06-canonical")
    window.pose.setCurrentIndex(1)
    window.style.setCurrentText("Textured")
    shot("07-target-pose")
    window.compare_toggle.setChecked(True)
    shot("08-comparison")
    window.diagnostics_toggle.setChecked(True)
    shot("09-diagnostics")
    window.engine.showPopup()
    app.processEvents()
    if not window.engine.view().window().grab().save(str(screenshots / "10-engine-menu.png")):
        raise RuntimeError("Could not capture the engine selector.")
    window.engine.hidePopup()
    window.compare_toggle.setChecked(False)

    start = perf_counter()
    window.ingest([photos / name for name in ("side.png", "threequarter.png")])
    profile["additional_import_seconds"] = perf_counter() - start
    assert window.active_result.id == single.id
    click_target(2)
    assert "TARGET" in window.photos.item(2).text()
    shot("03-target-selected")
    multi = attempt("B/F complementary references, C articulated target")
    assert multi.id != single.id
    click_target(0)
    changed = attempt("G changed target, same references")
    assert changed.metadata["canonical_id"] == multi.metadata["canonical_id"]
    assert changed.metadata["diagnostics"]["metrics"]["canonical_fit_reused"]
    assert changed.metadata["target_result_id"] == changed.id
    if geometry:
        window.engine.setCurrentIndex(window.engine.findData("geometry"))
        experimental = attempt("I Engine B, same references")
        assert experimental.metadata["diagnostics"]["executed_engine"] == "geometry"
        experiment_target = next(name for name in experimental.metadata["artifacts"] if name.startswith("target.usd"))
        window.service.export(experimental, output / f"experimental-{experiment_target}")
        click_target(2)
        experimental_changed = attempt("I/G Engine B, changed target")
        assert experimental_changed.metadata["canonical_id"] == experimental.metadata["canonical_id"]
        click_target(0)
        window.engine.setCurrentIndex(window.engine.findData(BASELINE))

    attempt("H cancel", cancel=True, expect="cancelled")
    kept = window.active_result.id
    retry = attempt("H retry")
    assert retry.id != kept
    window.ingest([photos / "blank.png"])
    click_target(3)
    adverse = attempt("D unsupported target with usable references")
    shot("11-unresolved-target")
    assert adverse.metadata["target_result_id"] is None
    assert any("Target pose unresolved" in warning for warning in adverse.metadata["diagnostics"]["warnings"])
    window.garment.setCurrentIndex(1)
    partial = attempt("E unavailable optional garment")
    assert partial.metadata["diagnostics"]["metrics"]["garment_status"].startswith("omitted")
    window.garment.setCurrentIndex(0)

    start = perf_counter()
    window.close()
    app.processEvents()
    window = EmpiricalWindow(engines, revision, settings=settings)
    window.show()
    QTest.qWaitForWindowExposed(window, 5000)
    app.processEvents()
    profile["warm_reopen_seconds_to_show"] = perf_counter() - start
    assert window.active_result.id == partial.id
    target = next(name for name in retry.metadata["artifacts"] if name.startswith("target.usd"))
    canonical = next(name for name in retry.metadata["artifacts"] if name.startswith("canonical.usd"))
    began = perf_counter()
    for name in (target, canonical):
        window.service.export(retry, output / name, target=name == target)
    profile["two_asset_copy_seconds"] = perf_counter() - began
    window.service.export_evidence(retry, output / "synthetic-diagnostics.zip")
    with ZipFile(output / "synthetic-diagnostics.zip") as archive:
        assert archive.testzip() is None
        assert not any(name.startswith("references/") for name in archive.namelist())
    profile["stages_observed_by_gui"] = list(dict.fromkeys(stages_seen))
    (output / "qualification.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    window.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA", "local development snapshot"))
    parser.add_argument("--geometry", action="store_true")
    args = parser.parse_args()
    qualify(args.assets.resolve(), args.output.resolve(), args.revision, geometry=args.geometry)
