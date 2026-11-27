"""Comprehensive integration & multi-agent unit test suite for AuditIQ MVP Backend.

Runs with standard `python3 -m unittest discover -s tests` (zero extra test dependencies)
and also works under pytest.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
from websocket import create_connection

from app.database import init_db, set_db_path
from app.main import app
from app.seed import ensure_seeded


class AuditIQBackendIntegrationTests(unittest.TestCase):
    server: uvicorn.Server
    thread: threading.Thread
    base_url: str
    ws_url: str
    temp_dir: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        db_file = Path(cls.temp_dir.name) / "test_auditiq.db"
        set_db_path(db_file)
        init_db()
        ensure_seeded()

        port = 18765
        cls.base_url = f"http://127.0.0.1:{port}"
        cls.ws_url = f"ws://127.0.0.1:{port}/ws/monitoring"
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()

        for _ in range(50):
            try:
                with urllib.request.urlopen(f"{cls.base_url}/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.should_exit = True
        cls.thread.join(timeout=3)
        cls.temp_dir.cleanup()

    def _request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def test_01_health_and_dashboard_seeded_60_tickets(self) -> None:
        code, health = self._request("GET", "/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(health["status"], "ok")

        code, dash = self._request("GET", "/api/dashboard")
        self.assertEqual(code, 200)
        self.assertEqual(dash["total"], 60)
        self.assertTrue(dash["isDemoData"])
        self.assertGreater(dash["compliance"], 70)
        self.assertGreaterEqual(dash["aiAlerts"], 3)
        self.assertIn("narrative", dash["managementInsight"])
        self.assertEqual(len(dash["samplingDistribution"]), 4)

    def test_02_queue_filters_and_facets(self) -> None:
        code, all_q = self._request("GET", "/api/tickets")
        self.assertEqual(code, 200)
        self.assertEqual(all_q["total"], 60)
        self.assertGreaterEqual(len(all_q["workload"]), 4)

        code, cr_high = self._request("GET", "/api/tickets?ticket_type=CR&risk=CRITICAL")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(cr_high["total"], 1)
        for item in cr_high["items"]:
            self.assertEqual(item["type"], "CR")
            self.assertEqual(item["riskBand"], "CRITICAL")

        code, search_q = self._request("GET", "/api/tickets?search=CR001992")
        self.assertEqual(code, 200)
        self.assertEqual(search_q["total"], 1)
        self.assertEqual(search_q["items"][0]["id"], "CR001992")

    def test_03_cr001992_end_to_end_10_step_demo_lifecycle(self) -> None:
        """Verifies Proposal Section 29 10-step E2E Demo: CR001992 missing business approval -> remediation -> LOW risk."""
        code, initial = self._request("GET", "/api/tickets/CR001992")
        self.assertEqual(code, 200)
        self.assertEqual(initial["type"], "CR")
        self.assertIn(initial["riskBand"], {"HIGH", "CRITICAL"})
        self.assertEqual(len(initial["agentTrace"]), 6)
        self.assertGreater(len(initial["highlights"]), 0)

        # Verify Business approval is initially FAIL
        biz_res = next(r for r in initial["results"] if r["criterion"] == "Business approval")
        self.assertEqual(biz_res["status"], "FAIL")

        # Verify Rollback plan is initially REVIEW (<80% confidence)
        rb_res = next(r for r in initial["results"] if r["criterion"] == "Rollback plan")
        self.assertEqual(rb_res["status"], "REVIEW")

        # Step 6: Upload business approval + rollback runbook + post validation + close ticket
        for action_type in ("business_approval", "rollback_plan", "post_validation", "close_ticket"):
            code, resp = self._request(
                "POST",
                "/api/tickets/CR001992/remediate",
                {"action_type": action_type, "actor": "Demo Presenter", "role": "Auditor"},
            )
            self.assertEqual(code, 200)

        # Verify CR001992 transitioned HIGH -> LOW with 100% compliance and PASS decision
        code, final = self._request("GET", "/api/tickets/CR001992")
        self.assertEqual(code, 200)
        self.assertEqual(final["riskBand"], "LOW")
        self.assertEqual(final["compliance"], 100.0)
        self.assertEqual(final["decision"], "PASS")
        self.assertEqual(final["state"], "Closed")
        self.assertGreaterEqual(len(final["auditTrail"]), 4)

    def test_04_human_override_and_closed_loop_learning_and_qc(self) -> None:
        code, inc = self._request("GET", "/api/tickets/INC0045810")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(inc["findings"]), 1)
        finding_id = inc["findings"][0]["findingId"]

        code, act = self._request(
            "POST",
            f"/api/tickets/INC0045810/findings/{finding_id}/action",
            {
                "decision": "OVERRIDE_PASS",
                "note": "Verified root cause inside linked problem record PRB00991.",
                "auditor": "A. Rahman",
                "role": "Auditor",
                "improvement_target": "Evidence Extraction",
            },
        )
        self.assertEqual(code, 200)
        self.assertIsNotNone(act["feedback"])
        self.assertTrue(act["auditTrailEntry"]["humanOverride"])

        # Check QC Intelligence reflects feedback loop
        code, qc = self._request("GET", "/api/qc")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(qc["feedbackCount"], 1)
        self.assertGreaterEqual(len(qc["auditors"]), 4)

        # Submit QC Verification on INC0045810's audit
        audit_id = inc["auditId"]
        code, qcr = self._request(
            "POST",
            f"/api/qc/reviews/{audit_id}",
            {
                "qc_status": "Verified",
                "qc_reviewer": "L. Chen (QC Lead)",
                "qc_note": "Confirmed problem record linkage.",
            },
        )
        self.assertEqual(code, 200)

    def test_05_copilot_and_rag_policy_knowledge_base(self) -> None:
        # Ticket-scoped question
        code, ans1 = self._request(
            "POST",
            "/api/copilot",
            {"ticket_id": "CR002010", "question": "Why did this ticket fail?"},
        )
        self.assertEqual(code, 200)
        self.assertIn("CR002010", ans1["answer"])
        self.assertGreater(len(ans1["sources"]), 0)

        # Fleet-wide approval query
        code, ans2 = self._request(
            "POST",
            "/api/copilot",
            {"ticket_id": "ALL", "question": "Show me all tickets missing approval."},
        )
        self.assertEqual(code, 200)
        self.assertGreater(len(ans2["referencedTickets"]), 0)

        # RAG policy search
        code, rag_res = self._request("GET", "/api/knowledge/search?q=business+approval+rollback+plan&ticket_type=CR")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(rag_res["hits"]), 1)
        self.assertEqual(rag_res["hits"][0]["policyId"], "POL-CHG-3.2")

    def test_06_live_monitoring_websocket_and_simulation(self) -> None:
        ws = create_connection(self.ws_url, timeout=5)
        try:
            welcome = json.loads(ws.recv())
            self.assertEqual(welcome["event"], "connected")

            code, sim = self._request("POST", "/api/monitoring/simulate", {})
            self.assertEqual(code, 200)
            sim_id = sim["ticket"]["id"]

            event_msg = json.loads(ws.recv())
            self.assertEqual(event_msg["event"], "audit_updated")
            self.assertEqual(event_msg["payload"]["ticketId"], sim_id)
            self.assertTrue(event_msg["payload"]["alertTriggered"])
        finally:
            ws.close()

        code, mon = self._request("GET", "/api/monitoring")
        self.assertEqual(code, 200)
        self.assertGreater(mon["activeTicketCount"], 0)
        self.assertGreater(len(mon["predictiveAudits"]), 0)

    def test_07_config_update_analytics_and_demo_reset(self) -> None:
        code, analytics = self._request("GET", "/api/analytics")
        self.assertEqual(code, 200)
        self.assertEqual(len(analytics["ticketType"]), 3)
        self.assertGreaterEqual(len(analytics["department"]), 5)
        self.assertGreaterEqual(len(analytics["trend"]), 6)

        code, cfg_resp = self._request(
            "PUT",
            "/api/config",
            {
                "confidence_auto": 94,
                "confidence_recommend": 78,
                "critical_risk_threshold": 82,
                "high_risk_threshold": 60,
                "medium_risk_threshold": 35,
                "medium_sampling_pct": 30,
                "proactive_alerts_enabled": True,
                "auto_close_low_risk": True,
                "updated_by": "Test Admin",
                "re_evaluate_all": True,
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(cfg_resp["config"]["confidenceAuto"], 94)

        # Reset demo cleanly restores CR001992 back to HIGH risk with 60 tickets
        code, reset = self._request("POST", "/api/config/reset-demo", {})
        self.assertEqual(code, 200)
        self.assertEqual(reset["tickets"], 60)
        code, cr_reset = self._request("GET", "/api/tickets/CR001992")
        self.assertIn(cr_reset["riskBand"], {"HIGH", "CRITICAL"})

    def test_08_csv_bulk_upload_and_create_ticket(self) -> None:
        # 1. Create single ticket via POST /api/tickets
        code, created = self._request(
            "POST",
            "/api/tickets",
            {
                "ticket_id": "CR009999",
                "ticket_type": "CR",
                "short_description": "Production payment switch kernel upgrade",
                "priority": "P1",
                "category": "Infrastructure",
                "business_unit": "Core Operations",
                "assignment_group": "Infrastructure",
                "status": "Scheduled",
                "sla_status": "At Risk",
                "work_notes": [{"author": "Ops", "text": "Technical review done; business approval missing and no rollback plan."}],
            },
        )
        self.assertEqual(code, 201)
        self.assertEqual(created["ticket"]["id"], "CR009999")
        self.assertIn(created["ticket"]["riskBand"], {"HIGH", "CRITICAL"})

        # 2. Multipart CSV bulk upload
        sample_csv = Path(__file__).resolve().parents[2] / "sample-data" / "sample_tickets.csv"
        boundary = "----AuditIQTestBoundary7MA4YWxkTrZu0gW"
        csv_bytes = sample_csv.read_bytes()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="sample_tickets.csv"\r\n'
            f"Content-Type: text/csv\r\n\r\n"
        ).encode("utf-8") + csv_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/tickets/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(res["processed"], 3)
        self.assertIn("CR009101", res["ticketIds"])
        self.assertGreaterEqual(res["highRisk"], 1)


if __name__ == "__main__":
    unittest.main()
