#!/usr/bin/env python3
"""Coherence check: signature-books vs the phone-book AI canon.

Every book lineage entry of kind "ai" cites a canon AI (JAH-AI-*). The
lineage stores the AI's NAME (as title) and a truncated DESCRIPTION
(blurb). This check verifies, for every AI-citing book:
  - the JAH-AI ID exists in the canon catalog
  - the name matches canon NAME exactly (whitespace-normalized)
  - the blurb is a prefix of canon DESCRIPTION (whitespace-normalized),
    since the lineage stores a truncated description
The per-book Q&A "Book Assistant" is a site helper (kind helper) and
claims no JAH-AI ID, so it is exempt from canon comparison.

Exit 0 = coherent. Exit 1 = DRIFT FOUND (loud report).
"""
import gzip
import glob
import json
import os
import re
import sys

CANON_PATH = os.path.expanduser(
    "~/workspace/jah-ai-models/ai-catalog.json")
VOLUMES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "volumes", "*.json.gz")


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def main():
    with open(CANON_PATH, encoding="utf-8") as f:
        canon_raw = json.load(f)
    canon = {}
    recs = canon_raw.get("records", canon_raw) if isinstance(canon_raw, dict) else canon_raw
    for r in recs:
        canon[str(r["ID"])] = (norm(r["NAME"]), norm(r.get("DESCRIPTION", "")))

    checked = 0
    issues = []
    for vf in glob.glob(VOLUMES):
        with gzip.open(vf, "rt", encoding="utf-8") as fh:
            recs = json.load(fh)
        for rec in recs:
            for s in rec.get("sources", []):
                if s.get("kind") != "ai":
                    continue
                checked += 1
                aid = norm(s.get("id"))
                label = s.get("label", "?")
                if aid not in canon:
                    issues.append(
                        f"UNKNOWN AI ID {aid} cited by {rec['id']} ({label})")
                    continue
                cname, cdesc = canon[aid]
                sname = norm(s.get("title"))
                # the label embeds "AI <name>" too; title is the authoritative field
                if sname and sname != cname:
                    issues.append(
                        f"NAME MISMATCH for {aid}: site shows '{sname}', canon is '{cname}' "
                        f"(book {rec['id']})")
                sblurb = norm(s.get("blurb"))
                if sblurb and not cdesc.startswith(sblurb):
                    issues.append(
                        f"DESCRIPTION DRIFT for {aid}: blurb '{sblurb[:80]}...' "
                        f"is not a prefix of canon description (book {rec['id']})")

    print(f"coherence_check (books): {checked} AI-citing lineage entries "
          f"checked against {len(canon)} canon AIs")
    if issues:
        print("*** COHERENCE DRIFT ***")
        for i in issues[:50]:
            print("  -", i)
        if len(issues) > 50:
            print(f"  ... and {len(issues) - 50} more")
        return 1
    print("OK: every cited AI matches the phone-book canon "
          "(helper 'Book Assistant' claims no canon ID — exempt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
