# Investigation: GMO Bt maize papers do not connect via CITES

## Hand-off Brief

1. **What happened.** User reports papers imported from `test-data/gmo-bt-maize` appear disconnected even though the HTML papers cite each other.
2. **Where the case stands.** Confirmed: Story 4.6 emits `CITES` only when extracted references match existing paper candidates by DOI exact or title similarity >= 0.85; current fixture title matching returns zero matches across the six HTML files.
3. **What's needed next.** Fix the matcher/import path around DOI persistence and Vietnamese/title-alias matching, then rerun graph extraction/backfill for the project.

## Case Info

| Field | Value |
| --- | --- |
| Ticket | N/A |
| Date opened | 2026-06-19 |
| Status | Active |
| System | Local workspace `/home/agent/github/C2-App-053` |
| Evidence sources | `test-data/gmo-bt-maize`, `backend/worker.py`, `reference_matcher.py`, `graph_extractor.py`, story 4.6 artifact |

## Problem Statement

User reports: after running story 4.6, papers in `/test-data/gmo-bt-maize` have no relationships in the knowledge map despite citing each other.

## Evidence Inventory

| Source | Status | Notes |
| --- | --- | --- |
| `test-data/gmo-bt-maize/*.html` | Available | Six fixture papers include DOI lines and cross-references in references sections. |
| `backend/worker.py` | Available | `graph_extract_task` writes `CITES` only after reference extraction and matching. |
| `reference_matcher.py` | Available | Matching is DOI exact first, then `SequenceMatcher` title ratio >= 0.85. |
| Runtime DB/Neo4j state | Missing | Not inspected; diagnosis is from source + fixture behavior. |

## Confirmed Findings

### Finding 1: CITES producer depends on reference matches

**Evidence:** `backend/worker.py:541`

**Detail:** References without a non-empty title are filtered out. If references exist, candidates are only papers in the same project, excluding self and deleted papers. Each matched candidate creates a `SyncOutboxORM(event_type="CITES")`.

### Finding 2: Matcher requires DOI exact or high title similarity

**Evidence:** `backend/src/modules/ingestion/infrastructure/reference_matcher.py:57`

**Detail:** DOI exact match returns immediately; otherwise title matching uses `difflib.SequenceMatcher` and requires `TITLE_MATCH_THRESHOLD = 0.85`.

### Finding 3: Fixture papers cite each other by DOI, but title variants are often below 0.85

**Evidence:** `test-data/gmo-bt-maize/02-meta-analysis-trai-chieu.html:265`, `test-data/gmo-bt-maize/02-meta-analysis-trai-chieu.html:273`, `test-data/gmo-bt-maize/05-phe-an-toan-5nam.html:356`, `test-data/gmo-bt-maize/05-phe-an-toan-5nam.html:359`, `test-data/gmo-bt-maize/05-phe-an-toan-5nam.html:363`

**Detail:** The fixture contains cross-citations to other fixture DOIs, but paper metadata titles and cited titles differ by subtitles, wording, and publication framing. A local script using the current matcher over parsed HTML titles found 0 matches among the six files.

### Finding 4: Vietnamese `đ/Đ` is not converted to `d`

**Evidence:** `backend/src/modules/ingestion/infrastructure/reference_matcher.py:25`

**Detail:** NFKD removes combining accents, but Vietnamese `đ` remains a base character and is then removed by `[^a-z0-9 ]+`. This weakens title similarity, though DOI matching should still work if DOI metadata is present.

## Deduced Conclusions

### Deduction 1: The UI graph is likely reflecting missing CITES events, not failing to draw existing edges

**Based on:** Findings 1 and 2.

**Reasoning:** Story 4.6 only creates Neo4j `CITES` edges after producer events. If no references match candidates, no event exists for the graph consumer to render.

**Conclusion:** The missing relationships are most likely upstream in reference matching/event production.

### Deduction 2: DOI persistence/extraction is the decisive path for this fixture

**Based on:** Findings 2 and 3.

**Reasoning:** Fixture cross-references include exact DOI values. If candidate `PaperORM.doi` and reference `doi` are both present, title similarity is irrelevant.

**Conclusion:** If graph is still disconnected, DOI was probably missing from stored paper metadata, missing from extracted references, or graph extraction was run before the full project had those candidate papers.

## Hypothesized Paths

### Hypothesis 1: Candidate papers lack DOI in DB

**Status:** Open

**Theory:** Metadata extraction or confirmation did not save DOI for the imported HTML papers, so matcher fell back to title matching and failed.

**Would confirm:** Query Postgres `papers` for this project and see null/incorrect DOI values.

**Would refute:** Stored `papers.doi` has the expected `10.1016/...`/`10.1111/...` values.

### Hypothesis 2: LLM reference extraction omitted DOI

**Status:** Open

**Theory:** `GraphExtractor` returned reference titles but not DOI values, pushing the flow to the brittle title matcher.

**Would confirm:** Worker logs or captured extractor output shows references without DOI.

**Would refute:** Extractor output includes correct DOI values.

### Hypothesis 3: Extraction order/backfill issue

**Status:** Open

**Theory:** Some papers were processed before their cited papers existed/indexed in the same project, and Story 4.6 does not automatically reprocess old papers when new candidates arrive.

**Would confirm:** Outbox/extraction timestamps show early papers processed before later papers were saved.

**Would refute:** Running graph extraction/backfill after all papers exist still creates no `CITES`.

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | --- | --- |
| Actual `papers.doi` values for the GMO project | Confirms whether DOI exact matching can work | Query Postgres for title, DOI, status, project_id |
| Extractor output for `references` | Confirms whether LLM returned DOI and clean titles | Add temporary log or inspect test/mock output |
| `sync_outbox` CITES rows | Confirms producer output | Query `sync_outbox` for `event_type='CITES'` |
| Neo4j `CITES` edges | Confirms consumer/render side | Query Neo4j `MATCH (:Paper)-[r:CITES]->(:Paper)` |

## Source Code Trace

| Element | Detail |
| --- | --- |
| Error origin | `backend/worker.py:541` through `backend/src/modules/ingestion/infrastructure/reference_matcher.py:57` |
| Trigger | `graph_extract_task` after a paper reaches `indexed` |
| Condition | References must exist and match same-project candidate papers by DOI or title similarity |
| Related files | `graph_extractor.py`, `metadata_extractor.py`, `neo4j_adapter.py` |

## Conclusion

**Confidence:** Medium

The evidence shows the fixture does contain cross-citations, but Story 4.6 will only produce graph edges when extracted references match stored paper metadata. Current title matching is too strict/brittle for the GMO fixture and Vietnamese normalization drops `đ`; DOI exact matching should save the case, so the remaining uncertainty is whether DOI is missing in stored paper metadata or missing in extracted references.

## Recommended Next Steps

### Fix direction

Strengthen deterministic matching: preserve Vietnamese `đ -> d`, add token/containment similarity for subtitle variants, and prefer DOI extraction/persistence verification in the upload flow. After fixing, rerun graph extraction/backfill for the project so old papers are reprocessed against the complete candidate set.

### Diagnostic

Query Postgres `papers` and `sync_outbox`, then query Neo4j for `CITES`. Add short logging around Story 4.6 output: references extracted, candidates count, matched IDs, unmatched references.

## Reproduction Plan

Parse the six HTML titles and reference list entries, feed them into `match_reference`, and assert expected edges. Current behavior: zero matches by title across the fixture when DOI is absent.

