#!/usr/bin/env python3
"""Provider-neutral ledger and candidate workspace for Recursive Specialization.

The first verified capability gap, correction, or process improvement is actionable:
``add`` records the observation and immediately creates or updates a private candidate.
The agent then edits that candidate and records a dogfood replay. A successful replay is
the promotion gate; recurrence is supporting evidence and a review nudge, not mandatory
waiting time.

The append-only JSONL ledger is shared by local provider adapters. It intentionally stores
compact evidence shapes rather than prompts or transcripts.

provenance: 2026-06-27, session 9f6014a0, original expert-accretion loop; revised
2026-07-18 after the owner corrected the recurrence-first design: learn, draft, and
dogfood on the first observation, including amendments to skills located by provenance.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import private_state

SCHEMA_VERSION = 2
DEFAULT_REVIEW_THRESHOLD = 3
STATUSES = ("open", "building", "built", "wontfix")
LEARNING_KINDS = ("gap", "correction", "improvement")
CANDIDATE_STATUSES = ("drafting", "validated", "rejected", "promoted")
DRAFT_MARKER = "<!-- candidate-draft: replace this marker after evidence-shaped authoring -->"


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _platform_state_home():
    override = os.environ.get("RECURSIVE_HARNESS_STATE_HOME", "").strip()
    if override:
        base = os.path.abspath(os.path.expanduser(override))
    elif os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        base = os.path.join(local, "RecursiveHarness")
    elif sys.platform == "darwin":
        base = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "RecursiveHarness"
        )
    else:
        xdg = os.environ.get("XDG_STATE_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "state"
        )
        base = os.path.join(xdg, "recursive-harness")
    return os.path.join(base, "specialization")


def resolve_state_dir(start=None):
    """Return the one provider-neutral local state directory.

    ``start`` is retained for caller compatibility; state is deliberately no longer tied
    to a checkout or worktree. Tests and callers that need isolation pass ``state_dir``
    directly to the public helpers.
    """
    del start
    return _platform_state_home()


def _ledger(state_dir=None):
    return os.path.join(state_dir or resolve_state_dir(), "skill_needs.jsonl")


def _candidate_root(state_dir=None):
    return os.path.join(state_dir or resolve_state_dir(), "candidates")


def _transaction_file(state_dir=None):
    return os.path.join(state_dir or resolve_state_dir(), "specialization.transaction")


def _candidate_dir(domain_key, state_dir=None):
    return os.path.join(_candidate_root(state_dir), _domain_key(domain_key))


def _domain_key(domain):
    return re.sub(r"[^a-z0-9]+", "-", (domain or "").lower()).strip("-") or "unknown"


def _domain_label(domain):
    """Keep untrusted domain text single-line before it enters YAML or a ledger."""
    return " ".join(str(domain or "").split())[:200] or "unknown"


def _nid(domain_key):
    return hashlib.sha1(domain_key.encode("utf-8")).hexdigest()[:6]


def _parse_tags(raw):
    return [item.strip() for item in (raw or "").replace("\n", ",").split(",") if item.strip()]


def _event_id(record):
    payload = {key: value for key, value in record.items() if key != "event_id"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _append(path, record, state_dir=None):
    row = dict(record)
    row.setdefault("schema_version", SCHEMA_VERSION)
    row.setdefault("event_id", _event_id(row))
    private_state.append_jsonl(path, row, root=state_dir or os.path.dirname(path))
    return row


def _read(path, state_dir=None):
    return private_state.read_jsonl(path, root=state_dir or os.path.dirname(path))


def _session_key(record):
    session = str(record.get("session") or "unknown")
    provider = str(record.get("provider") or "legacy")
    return f"{provider}:{session}"


def _aggregate(records):
    """Fold evidence, candidate, dogfood, and status events by normalized domain."""
    needs = {}
    for record in sorted(records, key=lambda row: row.get("ts", "")):
        raw_domain = record.get("domain") or record.get("domain_key")
        if not raw_domain:
            continue
        domain_key = _domain_key(str(raw_domain))
        need = needs.setdefault(domain_key, {
            "nid": _nid(domain_key),
            "domain_key": domain_key,
            "domain": record.get("domain", domain_key),
            "category": "general",
            "tags": [],
            "sessions": [],
            "shapes": [],
            "evidence_count": 0,
            "recurrence": 0,
            "status": "open",
            "skill": None,
            "learning_kinds": [],
            "target_skills": [],
            "candidate_status": None,
            "candidate_dir": None,
            "dogfoods": [],
            "first_ts": record.get("ts", ""),
            "last_ts": record.get("ts", ""),
        })
        need["last_ts"] = record.get("ts", need["last_ts"])
        if record.get("domain"):
            need["domain"] = record["domain"]
        kind = record.get("kind")
        if kind == "evidence":
            need["evidence_count"] += 1
            need["category"] = record.get("category", need["category"])
            for tag in record.get("tags", []):
                if tag not in need["tags"]:
                    need["tags"].append(tag)
            session_key = _session_key(record)
            if session_key not in need["sessions"]:
                need["sessions"].append(session_key)
            learning_kind = record.get("learning_kind", "gap")
            if learning_kind not in need["learning_kinds"]:
                need["learning_kinds"].append(learning_kind)
            target_skill = record.get("target_skill")
            if target_skill and target_skill not in need["target_skills"]:
                need["target_skills"].append(target_skill)
            if record.get("shape"):
                need["shapes"].append({
                    "ts": record.get("ts", ""),
                    "session": record.get("session"),
                    "provider": record.get("provider", "legacy"),
                    "learning_kind": learning_kind,
                    "event_id": record.get("event_id"),
                    "shape": record["shape"],
                })
        elif kind == "candidate":
            action = record.get("action")
            if action in CANDIDATE_STATUSES:
                need["candidate_status"] = action
            if record.get("candidate_dir"):
                need["candidate_dir"] = record["candidate_dir"]
        elif kind == "dogfood":
            need["dogfoods"].append(record)
        elif kind == "status":
            if record.get("status") in STATUSES:
                need["status"] = record["status"]
            if record.get("skill"):
                need["skill"] = record["skill"]
    for need in needs.values():
        need["recurrence"] = len(need["sessions"])
    return needs


def _all_needs(state_dir=None):
    state = state_dir or resolve_state_dir()
    aggregated = _aggregate(_read(_ledger(state), state))
    for domain_key, need in aggregated.items():
        if need["candidate_status"]:
            # Absolute user paths are intentionally sanitized in the ledger. Rebuild the
            # trusted local path from the state capability and normalized domain key.
            need["candidate_dir"] = _candidate_dir(domain_key, state)
    return aggregated


def promotable(threshold=None, state_dir=None):
    """Return proof-validated candidates. ``threshold`` is compatibility-only."""
    del threshold
    state = state_dir or resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        rows = [need for need in _all_needs(state).values()
                if need["status"] == "open" and need["candidate_status"] == "validated"]
    return sorted(rows, key=lambda need: (need["last_ts"], need["recurrence"]), reverse=True)


def reviewable(threshold=DEFAULT_REVIEW_THRESHOLD, state_dir=None):
    """Return unvalidated candidates whose independent-session evidence is recurring."""
    state = state_dir or resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        rows = [need for need in _all_needs(state).values()
                if need["status"] == "open"
                and need["candidate_status"] == "drafting"
                and need["recurrence"] >= threshold]
    return sorted(rows, key=lambda need: (-need["recurrence"], need["last_ts"]))


def attention_items(session=None, threshold=DEFAULT_REVIEW_THRESHOLD, state_dir=None):
    """Return candidates a lifecycle adapter should surface, highest-value first."""
    state = state_dir or resolve_state_dir()
    items = []
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        for need in _all_needs(state).values():
            if need["status"] != "open":
                continue
            if need["candidate_status"] == "validated":
                row = dict(need)
                row["attention"] = "promotion-ready"
                items.append(row)
            elif (session and any(key.endswith(f":{session}") for key in need["sessions"])
                  and need["candidate_status"] == "drafting"):
                row = dict(need)
                row["attention"] = "dogfood-now"
                items.append(row)
            elif need["candidate_status"] == "drafting" and need["recurrence"] >= threshold:
                row = dict(need)
                row["attention"] = "recurring-unvalidated"
                items.append(row)
    order = {"dogfood-now": 0, "promotion-ready": 1, "recurring-unvalidated": 2}
    return sorted(items, key=lambda row: (order[row["attention"]], -row["recurrence"]))


def claim_nudge(session, attention, state_dir=None):
    """Claim one lifecycle nudge per session and attention class."""
    state = state_dir or resolve_state_dir()
    safe = private_state.safe_filename_id(f"{session}:{attention}", "nudge")
    path = os.path.join(state, "nudges", safe + ".txt")
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        if private_state.path_exists(path, root=state):
            return False
        private_state.atomic_write_text(path, "nudged\n", root=state)
        return True


def _resolve_selector(needs, selector):
    selected = (selector or "").strip()
    for domain_key, need in needs.items():
        if selected in (need["nid"], domain_key):
            return domain_key
    lowered = selected.lower()
    hits = [domain_key for domain_key, need in needs.items()
            if lowered and (lowered in need["domain"].lower() or lowered in domain_key)]
    return hits[0] if len(hits) == 1 else None


def _read_candidate_manifest(path, state_dir):
    if not private_state.path_exists(path, root=state_dir):
        return {}
    try:
        value = private_state.read_json(path, root=state_dir)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _source_skill_name(content):
    """Read the small frontmatter name needed to bind an amendment to its owner."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.lower().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _resolve_named_input(path, filename, parent="", must_exist=True):
    """Resolve one explicit read-only input and enforce its documented shape."""
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw.strip() or "\0" in raw:
        raise ValueError(f"input must name {filename}")
    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(raw)))
    if os.path.basename(resolved) != filename:
        raise ValueError(f"input must name {filename}")
    if parent and os.path.basename(os.path.dirname(resolved)) != parent:
        raise ValueError(f"{filename} must be directly inside {parent}/")
    if must_exist and not os.path.isfile(resolved):
        raise ValueError(f"input must name a readable existing {filename}")
    return resolved


def _read_source_skill(path):
    resolved = _resolve_named_input(path, "SKILL.md")
    try:
        with open(resolved, encoding="utf-8") as stream:
            return stream.read()
    except (OSError, UnicodeError) as exc:
        raise ValueError("input must name a readable existing SKILL.md") from exc


def _candidate_seed(domain, domain_key, learning_kind, target_skill, event_id):
    skill_name = target_skill or f"{domain_key}-expert"
    second_case = ("\n- Replay a second materially distinct case for this new capability."
                   if learning_kind == "gap" else "")
    return f"""---
name: {skill_name}
description: Draft a precise trigger for the verified {domain} capability and its boundaries.
---

{DRAFT_MARKER}

# {domain}

## Procedure

- Replace this draft with the evidence-shaped procedure needed by the triggering case.
- Keep project-only facts outside this global candidate.

## Verification

- Replay the triggering case and record the before/after result with `needs.py candidate dogfood`.{second_case}

provenance: first-observation specialization candidate {event_id}; kind={learning_kind}
"""


def _mark_source_candidate(source):
    lines = source.splitlines()
    if lines and lines[0].strip() == "---":
        try:
            end = lines.index("---", 1)
            lines.insert(end + 1, "")
            lines.insert(end + 2, DRAFT_MARKER)
            return "\n".join(lines) + "\n"
        except ValueError:
            pass
    return DRAFT_MARKER + "\n\n" + source


def _ensure_candidate(record, source_content="", state_dir=None):
    state = state_dir or resolve_state_dir()
    domain_key = record["domain_key"]
    directory = _candidate_dir(domain_key, state)
    manifest_path = os.path.join(directory, "candidate.json")
    skill_path = os.path.join(directory, "SKILL.md")
    manifest = _read_candidate_manifest(manifest_path, state)
    previous_manifest = dict(manifest)
    created = not manifest
    previous_revision = int(manifest.get("revision", 0))
    revision = previous_revision + 1
    existing_target = manifest.get("target_skill") or None
    requested_target = record.get("target_skill") or None
    if existing_target and existing_target != requested_target:
        raise ValueError(
            f"candidate already belongs to target skill {existing_target!r}; "
            "continue with that owner or resolve the provenance collision"
        )
    rebase_from_source = bool(
        source_content and previous_manifest and requested_target
        and (not existing_target or previous_manifest.get("status") == "promoted")
    )
    evidence_ids = list(manifest.get("evidence_ids", []))
    if record["event_id"] not in evidence_ids:
        evidence_ids.append(record["event_id"])
    manifest.update({
        "schema_version": SCHEMA_VERSION,
        "domain": record["domain"],
        "domain_key": domain_key,
        "nid": _nid(domain_key),
        "learning_kind": record["learning_kind"],
        "target_skill": record.get("target_skill") or None,
        "target_provenance": record.get("target_provenance") or None,
        "status": "drafting",
        "revision": revision,
        "evidence_ids": evidence_ids,
        "updated_at": _now(),
    })
    manifest.pop("validated_at", None)
    manifest.pop("promoted_at", None)
    if not private_state.path_exists(skill_path, root=state):
        content = ""
        if source_content:
            content = _mark_source_candidate(source_content)
        if not content:
            content = _candidate_seed(
                record["domain"], domain_key, record["learning_kind"],
                record.get("target_skill", ""), record["event_id"]
            )
        private_state.atomic_write_text(skill_path, content, root=state)
    elif rebase_from_source:
        content = private_state.read_text(skill_path, root=state)
        archive_path = os.path.join(
            directory, "revisions", f"revision-{previous_revision}-before-rebase-SKILL.md"
        )
        private_state.atomic_write_text(archive_path, content, root=state)
        content = _mark_source_candidate(source_content)
        private_state.atomic_write_text(skill_path, content, root=state)
        manifest["rebased_at"] = _now()
        manifest["rebased_from_revision"] = previous_revision
    else:
        content = private_state.read_text(skill_path, root=state)
        if DRAFT_MARKER not in content:
            private_state.atomic_write_text(
                skill_path, _mark_source_candidate(content), root=state
            )
    private_state.atomic_write_json(manifest_path, manifest, root=state)
    prior = _all_needs(state).get(domain_key, {})
    if prior.get("status") == "built":
        _append(_ledger(state), {
            "ts": _now(),
            "kind": "status",
            "domain": record["domain"],
            "domain_key": domain_key,
            "status": "open",
            "session": record.get("session") or "unknown",
        }, state)
    _append(_ledger(state), {
        "ts": _now(),
        "kind": "candidate",
        "domain": record["domain"],
        "domain_key": domain_key,
        "action": "drafting",
        "candidate_dir": os.path.join("candidates", domain_key),
        "candidate_revision": revision,
        "source_event_id": record["event_id"],
        "rebased_from_source": rebase_from_source,
    }, state)
    return directory, created


def cmd_add(args):
    state = resolve_state_dir()
    source_content = ""
    if not args.domain.strip() or not args.shape.strip():
        print("domain and shape must contain non-whitespace evidence", file=sys.stderr)
        return 1
    if args.learning_kind == "gap" and any(str(value).strip() for value in (
            args.target_skill, args.target_provenance, args.source_skill)):
        print(
            "a gap has no provenance owner; use correction or improvement to amend a skill",
            file=sys.stderr,
        )
        return 1
    if args.learning_kind in ("correction", "improvement"):
        missing = [name for name, value in (
            ("--target-skill", args.target_skill),
            ("--target-provenance", args.target_provenance),
            ("--source-skill", args.source_skill),
        ) if not str(value).strip()]
        if missing:
            print(
                f"{args.learning_kind} must amend its provenance owner; required: "
                + ", ".join(missing),
                file=sys.stderr,
            )
            return 1
        try:
            source_content = _read_source_skill(args.source_skill)
        except ValueError as exc:
            print(f"--source-skill {exc}", file=sys.stderr)
            return 1
        source_name = _source_skill_name(source_content)
        if source_name != args.target_skill.strip():
            print(
                "--target-skill must match the name in --source-skill frontmatter",
                file=sys.stderr,
            )
            return 1
    domain = _domain_label(args.domain)
    domain_key = _domain_key(domain)
    session = (args.session or os.environ.get("CLAUDE_SESSION_ID")
               or os.environ.get("CODEX_SESSION_ID") or "unknown")
    provider = args.provider
    if provider == "auto":
        provider = "claude" if os.environ.get("CLAUDE_SESSION_ID") else (
            "codex" if os.environ.get("CODEX_SESSION_ID") else "unknown"
        )
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        existing_manifest = _read_candidate_manifest(
            os.path.join(_candidate_dir(domain_key, state), "candidate.json"), state
        )
        existing_target = existing_manifest.get("target_skill") or None
        requested_target = args.target_skill.strip() or None
        if existing_target and existing_target != requested_target:
            print(
                f"candidate already belongs to target skill {existing_target!r}; "
                "continue with that owner or resolve the provenance collision",
                file=sys.stderr,
            )
            return 1
        record = {
            "ts": _now(),
            "kind": "evidence",
            "learning_kind": args.learning_kind,
            "domain": domain,
            "domain_key": domain_key,
            "category": args.category,
            "tags": _parse_tags(args.tags),
            "shape": args.shape.strip(),
            "session": session,
            "turn": args.turn or None,
            "provider": provider,
            "repo": args.repo or None,
            "target_skill": args.target_skill or None,
            "target_provenance": args.target_provenance or None,
        }
        record = _append(_ledger(state), record, state)
        try:
            candidate_dir, created = _ensure_candidate(record, source_content, state)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"evidence logged but candidate creation failed: {exc}", file=sys.stderr)
            return 1
        need = _all_needs(state)[domain_key]
    verb = "created" if created else "updated"
    print(f"need {need['nid']} [{domain_key}] logged - evidence {need['evidence_count']}, "
          f"distinct sessions {need['recurrence']}")
    print(f"  candidate {verb}: {candidate_dir}")
    print("  edit the candidate now, replay the triggering case, then record: "
          f"needs.py candidate dogfood {need['nid']} ...")
    if need["recurrence"] >= args.threshold:
        print(f"  recurrence signal: observed in {need['recurrence']} distinct sessions; "
              "review urgently, but validate by dogfood rather than count alone.")
    return 0


def cmd_match(args):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        needs = _all_needs(state)
    selected = (args.domain or args.tags or "").lower()
    tags = set(_parse_tags(args.tags))
    hits = []
    for need in needs.values():
        if args.domain and (selected in need["domain"].lower() or selected in need["domain_key"]):
            hits.append(need)
        elif tags and tags.intersection(need["tags"]):
            hits.append(need)
    if not hits:
        print("no matching need - record the first observation and create its candidate now")
        return 0
    for need in sorted(hits, key=lambda row: (-row["recurrence"], -row["evidence_count"])):
        print(f"  {need['nid']}  sessions={need['recurrence']} evidence={need['evidence_count']} "
              f"[{need['status']}/{need['candidate_status'] or 'no-candidate'}] {need['domain']}")
    return 0


def _print_need(need, verbose=False):
    skill = f" -> {need['skill']}" if need["skill"] else ""
    print(f"  {need['nid']}  sessions={need['recurrence']} evidence={need['evidence_count']} "
          f"[{need['status']}/{need['candidate_status'] or 'no-candidate'}]{skill} {need['domain']}")
    print(f"        kinds={','.join(need['learning_kinds']) or '-'} "
          f"targets={','.join(need['target_skills']) or '-'} tags={','.join(need['tags']) or '-'}")
    if verbose:
        for shape in need["shapes"]:
            print(f"        - ({shape['ts'][:10]} {shape['provider']}:{str(shape['session'])[:8]} "
                  f"{shape['learning_kind']}) {shape['shape']}")
        for replay in need["dogfoods"]:
            print(f"        - dogfood {replay.get('outcome')} generalizes={replay.get('generalizes')} "
                  f"verification={replay.get('verification') or '-'}")


def cmd_list(args):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        needs = _all_needs(state)
    if args.domain:
        domain_key = _resolve_selector(needs, args.domain)
        if not domain_key:
            print(f"no single need matches {args.domain!r}", file=sys.stderr)
            return 1
        _print_need(needs[domain_key], verbose=True)
        return 0
    rows = [need for need in needs.values()
            if args.status == "all" or need["status"] == args.status]
    if not rows:
        print("ledger empty" if args.status == "all" else f"no needs with status={args.status}")
        return 0
    for need in sorted(rows, key=lambda row: (-row["recurrence"], -row["evidence_count"])):
        _print_need(need, verbose=args.verbose)
    return 0


def cmd_promote_check(args):
    ready = promotable(state_dir=resolve_state_dir())
    recurring = reviewable(args.threshold, resolve_state_dir())
    if args.json:
        print(json.dumps({"promotion_ready": ready, "recurring_unvalidated": recurring},
                         ensure_ascii=False))
        return 0
    if ready:
        print("PROMOTION-READY candidates (proof-validated; approval still required):")
        for need in ready:
            _print_need(need)
    if recurring:
        print("RECURRING but unvalidated candidates (finish dogfood; count is not proof):")
        for need in recurring:
            _print_need(need)
    if not ready and not recurring:
        print("no promotion-ready or recurring-unvalidated candidates")
    return 0


def _selected_need(selector, state_dir=None):
    state = state_dir or resolve_state_dir()
    needs = _all_needs(state)
    domain_key = _resolve_selector(needs, selector)
    if not domain_key:
        raise ValueError(f"no single need matches {selector!r}")
    return state, needs[domain_key]


def cmd_candidate_show(args):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        try:
            _state, need = _selected_need(args.selector, state)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    _print_need(need, verbose=True)
    print(f"        candidate={need['candidate_dir'] or _candidate_dir(need['domain_key'])}")
    return 0


def cmd_candidate_dogfood(args):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        try:
            _state, need = _selected_need(args.selector, state)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if need["status"] != "open" or need["candidate_status"] != "drafting":
            print("dogfood requires an open drafting candidate", file=sys.stderr)
            return 1
        if not all(value.strip() for value in (
                args.case, args.before, args.after, args.verification)):
            print("dogfood evidence fields must contain non-whitespace values", file=sys.stderr)
            return 1
        manifest = _read_candidate_manifest(
            os.path.join(_candidate_dir(need["domain_key"], state), "candidate.json"), state
        )
        revision = int(manifest.get("revision", 1))
        record = _append(_ledger(state), {
            "ts": _now(),
            "kind": "dogfood",
            "domain": need["domain"],
            "domain_key": need["domain_key"],
            "session": args.session or os.environ.get("CLAUDE_SESSION_ID")
                       or os.environ.get("CODEX_SESSION_ID") or "unknown",
            "provider": args.provider,
            "candidate_revision": revision,
            "case": args.case,
            "before": args.before,
            "after": args.after,
            "outcome": args.outcome,
            "generalizes": args.generalizes,
            "verification": args.verification,
        }, state)
    print(f"dogfood recorded for {need['nid']}: {record['outcome']} "
          f"(generalizes={record['generalizes']})")
    if record["outcome"] == "worked":
        print(f"  remove the candidate-draft marker after authoring, then run: "
              f"needs.py candidate validate {need['nid']}")
    return 0


def cmd_candidate_validate(args):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        try:
            _state, need = _selected_need(args.selector, state)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if need["status"] != "open" or need["candidate_status"] != "drafting":
            print("validation requires an open drafting candidate", file=sys.stderr)
            return 1
        directory = _candidate_dir(need["domain_key"], state)
        skill_path = os.path.join(directory, "SKILL.md")
        try:
            content = private_state.read_text(skill_path, root=state)
        except (OSError, ValueError) as exc:
            print(f"candidate SKILL.md unavailable: {exc}", file=sys.stderr)
            return 1
        if DRAFT_MARKER in content:
            print("candidate still carries the draft marker; author it before validation",
                  file=sys.stderr)
            return 1
        manifest_path = os.path.join(directory, "candidate.json")
        manifest = _read_candidate_manifest(manifest_path, state)
        revision = int(manifest.get("revision", 1))
        worked = [row for row in need["dogfoods"]
                  if row.get("outcome") == "worked"
                  and row.get("verification")
                  and int(row.get("candidate_revision", 0)) == revision]
        if not worked:
            print("validation requires a worked dogfood replay with verification evidence",
                  file=sys.stderr)
            return 1
        if manifest.get("learning_kind", "gap") == "gap":
            distinct_cases = {row.get("case", "").strip().casefold() for row in worked}
            distinct_cases.discard("")
            if len(distinct_cases) < 2 or not any(
                    row.get("generalizes") == "yes" for row in worked):
                print(
                    "a new capability requires two distinct worked cases for this revision, "
                    "including one marked generalizes=yes",
                    file=sys.stderr,
                )
                return 1
        _append(_ledger(state), {
            "ts": _now(),
            "kind": "candidate",
            "domain": need["domain"],
            "domain_key": need["domain_key"],
            "action": "validated",
            "candidate_dir": os.path.join("candidates", need["domain_key"]),
            "candidate_revision": revision,
            "verification_event_ids": [row.get("event_id") for row in worked],
        }, state)
        manifest["status"] = "validated"
        manifest["validated_at"] = _now()
        private_state.atomic_write_json(manifest_path, manifest, root=state)
    print(f"candidate {need['nid']} validated and promotion-ready; canonical changes still require approval")
    return 0


def _status_write(selector, new_status, skill=None):
    state = resolve_state_dir()
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        try:
            _state, need = _selected_need(selector, state)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if new_status == "built" and need["candidate_status"] != "validated":
            print("promotion requires a proof-validated candidate", file=sys.stderr)
            return 1
        _append(_ledger(state), {
            "ts": _now(),
            "kind": "status",
            "domain": need["domain"],
            "domain_key": need["domain_key"],
            "status": new_status,
            "skill": skill or None,
            "session": os.environ.get("CLAUDE_SESSION_ID")
                       or os.environ.get("CODEX_SESSION_ID") or "unknown",
        }, state)
        if new_status == "built":
            _append(_ledger(state), {
                "ts": _now(),
                "kind": "candidate",
                "domain": need["domain"],
                "domain_key": need["domain_key"],
                "action": "promoted",
                "candidate_dir": os.path.join("candidates", need["domain_key"]),
                "skill": skill or None,
            }, state)
            manifest_path = os.path.join(
                _candidate_dir(need["domain_key"], state), "candidate.json"
            )
            manifest = _read_candidate_manifest(manifest_path, state)
            manifest["status"] = "promoted"
            manifest["promoted_at"] = _now()
            private_state.atomic_write_json(manifest_path, manifest, root=state)
    print(f"need {need['nid']} [{need['domain_key']}] -> {new_status}"
          + (f" -> {skill}" if skill else ""))
    return 0


def cmd_status(args):
    return _status_write(args.selector, args.new_status, args.skill)


def cmd_promoted(args):
    return _status_write(args.selector, "built", args.skill)


def _normalize_legacy_record(value):
    """Remove path-bearing legacy fields and rebuild stable identity from its domain."""
    if not isinstance(value, dict):
        return None
    record = dict(value)
    raw_domain = str(record.get("domain") or record.get("domain_key") or "").strip()
    if not raw_domain:
        return None
    record["domain"] = _domain_label(record.get("domain") or raw_domain)
    record["domain_key"] = _domain_key(record["domain"])
    record.pop("candidate_dir", None)
    record["schema_version"] = int(record.get("schema_version") or 1)
    record["provider"] = str(record.get("provider") or "claude-legacy")
    if record.get("learning_kind") not in LEARNING_KINDS:
        record["learning_kind"] = "gap"
    if record["learning_kind"] == "gap":
        record.pop("target_skill", None)
        record.pop("target_provenance", None)
    record.pop("event_id", None)
    record["event_id"] = _event_id(record)
    return record


def cmd_migrate(args):
    state = resolve_state_dir()
    if not args.from_path:
        print(
            "migration requires --from-path <recursive-harness-checkout>/state/skill_needs.jsonl",
            file=sys.stderr,
        )
        return 2
    try:
        source = _resolve_named_input(
            args.from_path, "skill_needs.jsonl", "state", must_exist=False
        )
    except ValueError as exc:
        print(f"migration {exc}", file=sys.stderr)
        return 2
    if not os.path.exists(source):
        print(f"no legacy ledger at {source}; nothing to migrate")
        return 0
    if not os.path.isfile(source):
        print("migration input must name a readable existing skill_needs.jsonl", file=sys.stderr)
        return 2
    legacy = []
    with open(source, encoding="utf-8") as stream:
        for line in stream:
            try:
                row = _normalize_legacy_record(json.loads(line))
            except (TypeError, ValueError):
                continue
            if row:
                legacy.append(row)
    with private_state.exclusive_lock(_transaction_file(state), root=state):
        target = _ledger(state)
        current = _read(target, state)
        known = {row.get("event_id") or _event_id(row) for row in current}
        imported = [row for row in legacy if row["event_id"] not in known]
        if imported:
            private_state.rewrite_jsonl(target, current + imported, root=state)
        activated = 0
        records = _read(target, state)
        aggregated = _aggregate(records)
        for domain_key, need in aggregated.items():
            if (need["status"] != "open" or not need["evidence_count"]
                    or need["candidate_status"] is not None):
                continue
            evidence = next(
                row for row in reversed(records)
                if row.get("kind") == "evidence" and row.get("domain_key") == domain_key
            )
            _ensure_candidate(evidence, state_dir=state)
            activated += 1
        receipt_name = private_state.safe_filename_id(source, "migration") + ".json"
        private_state.atomic_write_json(os.path.join(state, "migrations", receipt_name), {
            "source": source,
            "source_records": len(legacy),
            "imported_records": len(imported),
            "completed_at": _now(),
        }, root=state)
    print(f"migration complete: imported {len(imported)} of {len(legacy)} legacy records; "
          f"activated {activated} candidates")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="needs.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    command = sub.add_parser("add", help="record evidence and create/update a candidate immediately")
    command.add_argument("--domain", required=True)
    command.add_argument("--shape", required=True)
    command.add_argument("--learning-kind", choices=LEARNING_KINDS, default="gap")
    command.add_argument("--category", default="general")
    command.add_argument("--tags", default="")
    command.add_argument("--session", default="")
    command.add_argument("--turn", default="")
    command.add_argument("--provider", default="auto")
    command.add_argument("--repo", default="")
    command.add_argument("--target-skill", default="")
    command.add_argument("--target-provenance", default="")
    command.add_argument("--source-skill", default="",
                         help="existing canonical SKILL.md to copy into an amendment candidate")
    command.add_argument("--threshold", type=int, default=DEFAULT_REVIEW_THRESHOLD)
    command.set_defaults(fn=cmd_add)

    command = sub.add_parser("match", help="recall related needs and skill targets")
    command.add_argument("--domain", default="")
    command.add_argument("--tags", default="")
    command.set_defaults(fn=cmd_match)

    command = sub.add_parser("list", help="show needs and their evidence/dogfood state")
    command.add_argument("--status", choices=[*STATUSES, "all"], default="open")
    command.add_argument("--domain", default="")
    command.add_argument("--verbose", action="store_true")
    command.set_defaults(fn=cmd_list)

    command = sub.add_parser("promote-check", help="show proof-ready and recurring candidates")
    command.add_argument("--threshold", type=int, default=DEFAULT_REVIEW_THRESHOLD)
    command.add_argument("--json", action="store_true")
    command.set_defaults(fn=cmd_promote_check)

    candidate = sub.add_parser("candidate", help="inspect, dogfood, and validate candidates")
    candidate_sub = candidate.add_subparsers(dest="candidate_cmd", required=True)
    command = candidate_sub.add_parser("show")
    command.add_argument("selector")
    command.set_defaults(fn=cmd_candidate_show)
    command = candidate_sub.add_parser("dogfood")
    command.add_argument("selector")
    command.add_argument("--case", required=True)
    command.add_argument("--before", required=True)
    command.add_argument("--after", required=True)
    command.add_argument("--outcome", choices=("worked", "failed", "partial"), required=True)
    command.add_argument("--generalizes", choices=("yes", "no", "unknown"), default="unknown")
    command.add_argument("--verification", required=True)
    command.add_argument("--session", default="")
    command.add_argument("--provider", default="unknown")
    command.set_defaults(fn=cmd_candidate_dogfood)
    command = candidate_sub.add_parser("validate")
    command.add_argument("selector")
    command.set_defaults(fn=cmd_candidate_validate)

    command = sub.add_parser("status", help="transition a need")
    command.add_argument("selector")
    command.add_argument("new_status", choices=STATUSES)
    command.add_argument("--skill", default="")
    command.set_defaults(fn=cmd_status)

    command = sub.add_parser("promoted", help="mark a validated candidate built")
    command.add_argument("selector")
    command.add_argument("--skill", required=True)
    command.set_defaults(fn=cmd_promoted)

    command = sub.add_parser("migrate", help="idempotently import an explicitly named legacy ledger")
    command.add_argument(
        "--from-path", default="",
        help="former Recursive Harness checkout's state/skill_needs.jsonl (required)",
    )
    command.set_defaults(fn=cmd_migrate)
    return parser


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
