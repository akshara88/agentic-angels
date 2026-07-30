"""
Run the Investment Committee swarm against a synthetic deal.

Inlines the founder pitch + third-party research into the user message (simpler
than Files API for hackathon-scale content). Streams events as they come in so
you can watch the five-way parallel fan-out, then the Risk cross-examination,
then the critic loop — this is the demo, narrate it live.

Saves the transcript to outputs/ and downloads whatever the agents wrote,
including outputs/ic-decision.md.

Usage:
    python run_deal_desk.py                       # seed-stage weighting
    IC_PROFILE=growth python run_deal_desk.py     # growth-stage weighting
"""

import os
from datetime import date
from pathlib import Path

from anthropic import Anthropic


# Founder-authored. Everything in it is UNVERIFIED by construction.
DEAL_PATH = Path("synthetic-data/pitch-nimbus-health.md")

# Third-party. These may be cited as verified evidence. The asymmetry between
# these and DEAL_PATH is the point — it drives the memo's verification section.
SUPPORTING_FILES = [
    Path("synthetic-data/market-report.md"),
    Path("synthetic-data/competitor-landscape.json"),
    Path("synthetic-data/saas-benchmarks.json"),
]
OUTPUT_DIR = Path("outputs")

# The Chair applies one of these. The weight tables live in the
# ic-memo-standard skill; only the profile name travels in the kickoff.
WEIGHTING_PROFILES = ("seed", "growth")


def load_inputs_as_context() -> str:
    blocks = []
    for path in [DEAL_PATH, *SUPPORTING_FILES]:
        if not path.exists():
            print(f"  WARNING: {path} missing — skipping")
            continue
        print(f"  including {path.name}")
        blocks.append(f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}")
    return "\n\n".join(blocks)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    if not Path(".coordinator_id").exists() or not Path(".environment_id").exists():
        raise SystemExit(
            "Missing .coordinator_id or .environment_id. Run "
            "create_specialists.py, upload_skills.py, then create_coordinator.py first."
        )

    coordinator_id = Path(".coordinator_id").read_text().strip()
    environment_id = Path(".environment_id").read_text().strip()

    profile = os.environ.get("IC_PROFILE", "seed").strip().lower()
    if profile not in WEIGHTING_PROFILES:
        raise SystemExit(
            f"IC_PROFILE must be one of {WEIGHTING_PROFILES}, got {profile!r}"
        )

    client = Anthropic()

    print("Loading deal materials...")
    context = load_inputs_as_context()

    research_date = date.today().isoformat()
    print(f"\nStarting session against coordinator {coordinator_id}...")
    print(f"  weighting profile: {profile}   research date: {research_date}")
    session = client.beta.sessions.create(
        agent=coordinator_id,
        environment_id=environment_id,
        title=f"IC — {DEAL_PATH.stem} ({profile})",
    )
    Path(".last_session_id").write_text(session.id)

    user_message = (
        "A startup has been submitted to the Investment Committee for a funding "
        "decision. Chair the committee end to end.\n\n"
        f"RESEARCH DATE: {research_date}\n"
        f"WEIGHTING PROFILE: {profile}\n\n"
        "Run all four stages:\n"
        "1. Read the documents yourself.\n"
        "2. Delegate to all FIVE due-diligence lenses IN PARALLEL, in one turn.\n"
        "3. Then delegate to the Risk Specialist, pasting all five reports into "
        "its brief VERBATIM — it cannot see your conversation.\n"
        "4. Draft the memo using the ic-memo-standard skill, then run the "
        "critic loop with the IC Critic (max two revisions), and write the "
        "final memo to outputs/ic-decision.md.\n\n"
        "The first document below is founder-provided and UNVERIFIED. The rest "
        "are third-party and may be cited as verified. Do not run web searches "
        "— everything you need is here.\n\n"
        f"{context}"
    )

    # Stream the events — this is the demo. Watch for parallel thread spawns.
    print("\n=== EVENT STREAM (this is the demo) ===\n")
    final_text_parts: list[str] = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )
        for event in stream:
            t = event.type
            if t == "session.thread_created":
                print(f"  [thread spawned]   {event.agent_name}", flush=True)
            elif t == "session.thread_status_running":
                name = getattr(event, "agent_name", "?")
                print(f"  [thread running]   {name}", flush=True)
            elif t == "agent.thread_message_received":
                print(f"  [reply ←]          {event.from_agent_name}", flush=True)
                # Make the critic loop legible on the stream.
                reply = " ".join(
                    b.text for b in (event.content or [])
                    if getattr(b, "type", None) == "text"
                )
                if "VERDICT:" in reply:
                    verdict = reply.split("VERDICT:", 1)[1].strip().split("\n")[0]
                    print(f"  [VERDICT]          {verdict[:60]}", flush=True)
            elif t == "agent.thread_message_sent":
                print(f"  [delegate →]       {event.to_agent_name}", flush=True)
            elif t == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif t == "agent.tool_use":
                print(f"\n  [tool: {getattr(event, 'name', '?')}]", flush=True)
            elif t == "session.error":
                print(f"\n  [session error]    {getattr(event, 'message', event)}",
                      flush=True)
            elif t == "session.status_terminated":
                print("\n\n[session terminated]")
                break
            elif t == "session.status_idle":
                # Idle is not automatically terminal: the session also parks here
                # when it needs something from us. Only a non-requires_action
                # stop_reason means the committee is actually done.
                stop = getattr(event, "stop_reason", None)
                if getattr(stop, "type", None) == "requires_action":
                    continue
                print("\n\n[committee finished]")
                break

    OUTPUT_DIR.mkdir(exist_ok=True)
    transcript_path = OUTPUT_DIR / "coordinator-transcript.txt"
    transcript_path.write_text("".join(final_text_parts))
    print(f"\nCoordinator transcript saved to {transcript_path}")

    # Pull every file the agents produced in the container
    print("\nDownloading deliverables from the session container...")
    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )
    file_count = 0
    for f in files.data:
        out_path = OUTPUT_DIR / f.filename
        print(f"  {f.filename}  ->  {out_path}")
        content = client.beta.files.download(f.id)
        content.write_to_file(str(out_path))
        file_count += 1

    if file_count == 0:
        print("  (no files found — agents may have produced text-only output)")
    else:
        print(f"\nDownloaded {file_count} file(s) to {OUTPUT_DIR}/")

    print(f"\nView the full session (including all sub-agent threads) at:")
    print(f"  https://platform.claude.com/sessions/{session.id}")


if __name__ == "__main__":
    main()
