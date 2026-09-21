from __future__ import annotations


def format_conflict_alert(node_name: str, claims: list[dict]) -> str:
    """Formats the DM sent to each party in a conflict.

    Asks them to reconcile — never asserts blame, per PRD.md §15's non-goal (no employee-
    performance monitoring). This is a request for input, not a judgment about anyone.
    """
    lines = [f"Project Brain noticed conflicting information about *{node_name}*:"]
    for claim in claims:
        lines.append(f"  - {claim['source_type']}: {claim['claimed_state']}")
    lines.append("Could you help reconcile this?")
    return "\n".join(lines)


def resolve_slack_recipient(claim: dict, identity_links: dict) -> str | None:
    """Maps a claim's author to a Slack user id to DM.

    A Slack-sourced claim's author already *is* a Slack user id. A GitHub-sourced claim's
    author is a GitHub login, resolved via a manual mapping (docs/roadmap-v2.md: no
    automatic cross-platform identity inference for MVP). Returns None when the author is
    missing or unmapped — never guessed at, matching PRD.md §6's "unknown is valid."
    """
    author = claim.get("author")
    if not author:
        return None
    if claim.get("source_type") == "slack":
        return author
    return identity_links.get(author)
