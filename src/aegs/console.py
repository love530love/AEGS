from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from .core import AEGSError, decide, list_proposals, read_json, record_feedback, verify


def _field(values: dict[str, list[str]], name: str) -> str | None:
    value = values.get(name, [None])[0]
    return value.strip() if value else None


def render_console(root: Path, notice: str = "") -> str:
    check = verify(root)
    charter = read_json(root / ".aegs" / "charter.json")
    cards = []
    for proposal in list_proposals(root):
        if proposal.get("status") != "DRAFT":
            continue
        risk = escape(proposal["risk"])
        cards.append(
            f"""<article class='card'>
<h3>{escape(proposal['title'])} <span class='risk {risk}'>{risk}</span></h3>
<p><code>{escape(proposal['proposal_id'])}</code> · proposer: {escape(proposal['proposer'])}</p>
<dl><dt>Baseline</dt><dd>{escape(str(proposal.get('baseline_git_head') or 'not a Git repository'))}</dd>
<dt>Evidence</dt><dd>{escape(', '.join(proposal.get('evidence_refs', [])) or 'No supporting evidence recorded')}</dd>
<dt>Counter-evidence</dt><dd>Not yet captured — do not infer that none exists.</dd>
<dt>Rollback</dt><dd>{escape(str(proposal.get('rollback_reference') or 'Not yet provided'))}</dd></dl>
<form method='post' action='/decision'>
<input type='hidden' name='proposal_id' value='{escape(proposal['proposal_id'])}'>
<label>Owner <select name='approver'>{''.join(f"<option>{escape(owner)}</option>" for owner in charter['owners'])}</select></label>
<label>Evidence reference <input name='evidence' placeholder='Required to approve YELLOW/RED'></label>
<label>Rollback reference <input name='rollback' placeholder='Required to approve YELLOW/RED'></label>
<div class='actions'><button name='action' value='APPROVE'>Approve</button><button name='action' value='REJECT'>Reject</button><button name='action' value='DEFER'>Defer</button><button name='action' value='HOLD'>Freeze candidate</button></div>
</form></article>"""
        )
    inbox = "".join(cards) or "<p class='empty'>No DRAFT proposals. Agents may propose; they cannot silently promote a change.</p>"
    status = "PASS" if check["ok"] else "HOLD"
    errors = "<br>".join(escape(error) for error in check["errors"]) or "No verification errors."
    return f"""<!doctype html><html lang='en'><meta charset='utf-8'><title>AEGS Human Governance Console</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;background:#f7f8fa;color:#1d2939}} .banner{{padding:1rem;border:2px solid #b42318;background:#fef3f2}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:1rem}} .card{{background:white;padding:1rem;border:1px solid #d0d5dd;border-radius:8px}} label{{display:block;margin:.6rem 0;font-weight:600}} input,select,textarea{{display:block;width:100%;box-sizing:border-box;margin-top:.2rem;padding:.45rem}} button{{padding:.5rem .75rem;margin:.2rem}} .risk{{padding:.15rem .4rem;border-radius:4px;font-size:.75rem}} .GREEN{{background:#d1fadf}} .YELLOW{{background:#fef0c7}} .RED{{background:#fee4e2}} dt{{font-weight:700}} dd{{margin:0 0 .45rem}} .empty{{color:#475467}}</style>
<main><h1>AEGS Human Governance Console</h1>
<section class='banner'><strong>Local prototype only.</strong> This console binds to localhost and has no authentication. Owner identity is self-declared; do not expose it on a network or treat it as production authorization.</section>
<p><strong>Governance verification: {status}</strong> · ledger events: {check['ledger_events']}<br>{errors}</p>
<h2>Decision inbox</h2>{inbox}
<h2>Feedback studio</h2><section class='card'><p>Feedback is stored only after explicit confirmation. A preference is not silently promoted into a lasting rule.</p>
<form method='post' action='/feedback'><label>Author <select name='author'>{''.join(f"<option>{escape(owner)}</option>" for owner in charter['owners'])}</select></label>
<label>Type <select name='kind'><option value='preference'>Temporary preference</option><option value='constraint'>Project constraint</option><option value='fact_correction'>Fact correction</option><option value='hypothesis'>Hypothesis</option></select></label>
<label>Scope <select name='scope'><option value='task'>Current task</option><option value='project'>Current project</option><option value='project_group'>Project group</option><option value='global_candidate'>Global candidate</option></select></label>
<label>Duration <select name='duration'><option value='once'>Once</option><option value='task_end'>Until task end</option><option value='expires_at'>Explicit expiry required later</option><option value='persistent'>Persistent</option></select></label>
<label>Confidence <select name='confidence'><option value='certain'>Certain</option><option value='preference'>Preference</option><option value='exploratory'>Exploratory</option></select></label>
<label>Feedback <textarea required name='source_text' rows='4' placeholder='What should change, and why?'></textarea></label>
<label><input type='checkbox' name='confirmed' value='yes'> I have checked the type, scope, duration and confidence.</label><button>Record confirmed feedback</button></form></section>
<h2>Decision hygiene</h2><p>High-risk decisions must include counter-evidence, impact and a rollback path. This prototype permits a candidate freeze through <code>HOLD</code>; release rollback will be added only after versioned release artifacts exist.</p>
{f'<p class="notice">{escape(notice)}</p>' if notice else ''}</main></html>"""


def serve(root_value: str | Path, port: int) -> None:
    root = Path(root_value).expanduser().resolve()

    class ConsoleHandler(BaseHTTPRequestHandler):
        def _respond(self, page: str, status: int = 200) -> None:
            data = page.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/":
                self._respond(render_console(root, "Not found"), 404)
                return
            self._respond(render_console(root))

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            values = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            try:
                if self.path == "/decision":
                    decide(root, _field(values, "proposal_id") or "", _field(values, "action") or "", _field(values, "approver") or "", _field(values, "evidence"), _field(values, "rollback"))
                    message = "Decision recorded in the event ledger."
                elif self.path == "/feedback":
                    record_feedback(root, _field(values, "author") or "", _field(values, "kind") or "", _field(values, "scope") or "", _field(values, "duration") or "", _field(values, "confidence") or "", _field(values, "source_text") or "", _field(values, "confirmed") == "yes")
                    message = "Confirmed feedback recorded as a HumanDirective."
                else:
                    self._respond(render_console(root, "Not found"), 404)
                    return
            except AEGSError as error:
                self._respond(render_console(root, f"Action rejected: {error}"), 400)
                return
            self.send_response(303)
            self.send_header("Location", f"/?notice={escape(message)}")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    print(f"AEGS console: http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop. This local prototype has no authentication.")
    ThreadingHTTPServer(("127.0.0.1", port), ConsoleHandler).serve_forever()
