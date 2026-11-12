"""Tests for w5run.py. Run: python3 -m unittest discover -s project/tools -v"""
import copy
import csv
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import w5run  # noqa: E402

GOOD = {
    "schema": "scc26-week5-run/1",
    "run_id": "20261110T090000Z-w5-phase1-defend",
    "scenario_id": "S-01",
    "phase": 1,
    "team_role": "defender",
    "authorisation": {"roe_reference": "issue-102", "acknowledged_utc": "2026-11-10T08:00:00Z"},
    "frozen": {"git_sha": "8e013b4" + "0" * 33, "images": {"platform": "ghcr.io/x/y@sha256:" + "a" * 64}},
    "scope": {"sources": ["peer-range-host"], "targets": ["edge-01"]},
    "time_sync": {"checked_utc": "2026-11-10T08:30:00Z", "max_skew_seconds": 0.02},
    "baseline": {"start_utc": "2026-11-10T08:40:00Z", "end_utc": "2026-11-10T08:55:00Z", "evidence": []},
    "window": {"start_utc": "2026-11-10T09:00:00Z", "end_utc": "2026-11-10T09:40:00Z"},
    "expected_layers": ["host", "network"],
    "evidence": [{"id": "E1", "layer": "network", "source": "suricata-eve", "path": "x", "sha256": "b" * 64}],
    "detections": [{"id": "D1", "utc": "2026-11-10T09:02:30Z", "source": "wazuh", "rule": "86601", "evidence_id": "E1"}],
    "milestones": {
        "first_detection_utc": "2026-11-10T09:02:30Z",
        "identified_utc": "2026-11-10T09:10:00Z",
        "contained_utc": "",
        "recovered_utc": "",
    },
    "acp": [{"task_id": "t1", "human_review": "corrected one claim"}],
    "findings": {"false_positives": ["fp1"], "false_negatives": [], "gaps": []},
    "reset_replay": "docs/week5-runbook.md#reset-and-replay",
}


class Validate(unittest.TestCase):
    def test_good_manifest_passes_both_stages(self):
        self.assertEqual(w5run.validate(GOOD, "plan"), [])
        self.assertEqual(w5run.validate(GOOD, "final"), [])

    def test_template_is_refused_until_filled(self):
        import yaml

        raw = (pathlib.Path(__file__).parents[1] / "runs/_template/manifest.yaml").read_text(encoding="utf-8")
        errs = w5run.validate(yaml.safe_load(raw), "plan", raw)
        self.assertTrue(any("roe_reference" in e for e in errs))
        self.assertTrue(any("scenario_id" in e for e in errs))

    def test_no_exercise_without_roe(self):
        m = copy.deepcopy(GOOD)
        m["authorisation"]["roe_reference"] = ""
        self.assertTrue(any("Rules of Engagement" in e for e in w5run.validate(m, "plan")))

    def test_real_ip_refused_doc_range_allowed(self):
        self.assertTrue(w5run.scan_public_safe("target: 10.20.30.40", "x"))
        self.assertTrue(w5run.scan_public_safe("target: 100.64.7.9/32.", "x"))
        self.assertEqual(w5run.scan_public_safe("target: 198.51.100.7", "x"), [])
        self.assertEqual(w5run.scan_public_safe("version 1.20.1.4x", "x"), [])

    def test_secret_refused(self):
        self.assertTrue(w5run.scan_public_safe("password: hunter2", "x"))
        self.assertTrue(w5run.scan_public_safe("Bearer eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJ4In0.sig", "x"))

    def test_skew_baseline_and_order(self):
        m = copy.deepcopy(GOOD)
        m["time_sync"]["max_skew_seconds"] = 2.5
        m["baseline"]["end_utc"] = "2026-11-10T08:45:00Z"
        m["authorisation"]["acknowledged_utc"] = "2026-11-10T09:30:00Z"
        errs = " ".join(w5run.validate(m, "plan"))
        self.assertIn("not defensible", errs)
        self.assertIn("10-15 minutes", errs)
        self.assertIn("before the scenario starts", errs)

    def test_unpinned_image_and_non_logical_target(self):
        m = copy.deepcopy(GOOD)
        m["frozen"]["images"]["platform"] = "ghcr.io/x/y:latest"
        m["scope"]["targets"] = ["Edge 01"]
        errs = " ".join(w5run.validate(m, "plan"))
        self.assertIn("sha256", errs)
        self.assertIn("logical name", errs)

    def test_final_needs_review_and_records_misses(self):
        m = copy.deepcopy(GOOD)
        m["detections"] = []
        m["acp"][0]["human_review"] = ""
        errs = " ".join(w5run.validate(m, "final"))
        self.assertIn("false_negatives", errs)
        self.assertIn("human must review", errs)
        m["findings"]["false_negatives"] = ["no alert for step 2"]
        m["acp"][0]["human_review"] = "ok"
        self.assertEqual(w5run.validate(m, "final"), [])


class Metrics(unittest.TestCase):
    def test_metrics_and_nulls(self):
        r = w5run.metrics(GOOD)
        self.assertEqual(r["T_detect_s"], 150)
        self.assertEqual(r["T_identify_s"], 450)
        self.assertIsNone(r["T_contain_s"])
        self.assertIsNone(r["T_recover_s"])
        self.assertEqual(r["false_positives"], 1)

    def test_out_of_order_refused(self):
        m = copy.deepcopy(GOOD)
        m["milestones"]["identified_utc"] = "2026-11-10T09:01:00Z"
        with self.assertRaises(w5run.Invalid):
            w5run.metrics(m)


class Timeline(unittest.TestCase):
    def _csv(self, d, name, rows):
        p = pathlib.Path(d) / name
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(w5run.TIMELINE_FIELDS)
            w.writerows(rows)
        return p

    def test_merge_sorts_dedupes_and_writes_md(self):
        with tempfile.TemporaryDirectory() as d:
            a = self._csv(d, "a.csv", [["2026-11-10T09:05:00Z", "wazuh", "host", "E2", "rule 5710"]])
            b = self._csv(
                d,
                "b.csv",
                [
                    ["2026-11-10T09:02:00Z", "suricata", "network", "E1", "scan | burst"],
                    ["2026-11-10T09:05:00Z", "wazuh", "host", "E2", "rule 5710"],
                ],
            )
            out, md = pathlib.Path(d) / "t.csv", pathlib.Path(d) / "t.md"
            self.assertEqual(w5run.main(["timeline", str(a), str(b), "-o", str(out), "--md", str(md)]), 0)
            rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
            self.assertEqual([r["evidence_id"] for r in rows], ["E1", "E2"])
            self.assertIn("scan / burst", md.read_text(encoding="utf-8"))

    def test_merge_refuses_ip_and_uncited_rows(self):
        with tempfile.TemporaryDirectory() as d:
            bad_ip = self._csv(d, "a.csv", [["2026-11-10T09:05:00Z", "wazuh", "host", "E2", "from 10.1.2.3"]])
            with self.assertRaises(w5run.Invalid):
                w5run.merge_timeline([bad_ip])
            uncited = self._csv(d, "b.csv", [["2026-11-10T09:05:00Z", "wazuh", "host", "", "x"]])
            with self.assertRaises(w5run.Invalid):
                w5run.merge_timeline([uncited])


class Figures(unittest.TestCase):
    def test_example_run_renders_figures_and_tables(self):
        try:
            import w5figures
        except ImportError:  # matplotlib not installed locally
            self.skipTest("matplotlib not installed")
        example = pathlib.Path(__file__).parent / "testdata/example-run"
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(w5figures.main([str(example), "-o", d]), 0)
            names = {p.name for p in pathlib.Path(d).iterdir()}
            for n in ("phases.pdf", "phases.png", "metrics.tex", "metrics.md",
                      "timeline-20261110T090000Z-w5-example-defend.png"):
                self.assertIn(n, names)
            md = (pathlib.Path(d) / "metrics.md").read_text(encoding="utf-8")
            self.assertIn("2.5 min", md)  # T_detect 150 s
            self.assertIn("not reached", md)  # T_recover is never imputed

    def test_example_manifest_is_valid(self):
        import yaml

        raw = (pathlib.Path(__file__).parent / "testdata/example-run/manifest.yaml").read_text(encoding="utf-8")
        self.assertEqual(w5run.validate(yaml.safe_load(raw), "final", raw), [])


if __name__ == "__main__":
    unittest.main()
