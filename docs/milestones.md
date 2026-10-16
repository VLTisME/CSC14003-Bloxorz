# Project milestones

Updated 16 October 2026. Dates use Asia/Ho_Chi_Minh. Check an item only when its listed deliverables exist and verification passes. A completed repository milestone does not imply its prose has already been transferred to Prism; report synchronization is tracked separately below.

## Completed preparation

- [x] **M0 — Finalize problem formulation v1.0.** Completed **2026-10-15**. JSON input/output, movement illustration, special tiles, free cube selection, one cost per directional move, small-cube fragile/goal behaviour, and AC/WA/RE rules are documented. Report structure has been accepted. Evidence: [statement](problem-statement.md), [runner plan](runner-proposal.md). Report contribution ready: problem formulation and system-boundary description.

- [x] **M1 — Build the supplied test suite and simple checker.** Completed **2026-10-15**. 33 original-stage input/output pairs and six solvable examples are present. All 39 reference paths pass replay; ten checker regression tests pass. Stage 15 has a verified 57-move replacement for the problematic upstream path. Provenance and reference-length limits are recorded. Evidence: [test guide](../testcases/README.md), [manifest](../testcases/manifest.json), [source notes](stage-sources.md), [checker](../checker.py). Report contribution ready: dataset provenance, checker method, and validation notes.

- [x] **M1.1 — Shared measurement helper and author handoff.** Completed **2026-10-16**. Added the helper, copyable algorithm template, required benchmark-output fields, metric definitions, and author guide. All 21 regression tests pass, including 11 helper tests; all 39 reference paths still pass replay. Agreed submission commands are documented but not implemented. Evidence: [helper](../algorithms/solver_support.py), [template](../algorithms/template.py), [guide](algorithm-guide.md), [tests](../tests/test_solver_support.py). Report contribution ready: measurement protocol, benchmark-completeness policy, and verification evidence.

## Remaining milestones

- [ ] **M2 — Assign work and transfer the preparation into Prism.** Completion date: pending. Allocate all four algorithms and the engine work after the formulation/test review. Keep names, personal checklists, and completion percentages in the report only. Update Google Docs when separately requested. Report: planning table, formulation, test-suite provenance, and future-work note.

- [ ] **M3 — Game engine and terminal 2D visualization.** Completion date: pending. Manual play and replay work with all required mechanics; state transitions agree with the checker and examples. Report: state/transition design, implementation decisions, verification evidence.

- [ ] **M4 — Four standalone Python search programs.** Completion date: pending. BFS, DFS/IDS, UCS, and A* consume stage JSON and return replayable JSON. Each records the required search metrics. Explain unit-cost UCS/BFS equivalence and justify the A* heuristic. Report: four algorithm subsections, costs, correctness conditions, complexity.

- [ ] **M5 — Complete Phase 1 integration.** Completion date: pending. The submission checker and runner share program execution, limits, and replay. Both report verdict totals; the runner additionally records benchmark completeness, statistics, one timestamped results JSON, and terminal replay. Report: experiment method and first measured tables; no invented results.

- [ ] **M6 — 3D GUI and final evaluation.** Completion date: pending. 3D manual play and automatic solution playback work. Run a fixed benchmark, generate charts, discuss time/memory/expansion/length tradeoffs. Report: GUI description, final results and discussion.

- [ ] **M7 — Submission package and demo.** Completion date: pending. Reproducible source, setup instructions, PDF, citations, AI-use appendix, public narrated/subtitled demo link, and correctly named archive are complete. Report: final cross-check against the assignment rubric.

M3 and M4 can proceed in parallel after assignment. No implementation or performance milestone has been marked complete merely because a plan exists. The earlier 15–20 October Phase 1 window was a planning target; an absolute submission deadline has not been verified.

## Publication status

- [x] Local files prepared for the documentation/test-case package — **2026-10-15**.
- [x] Measurement-helper and output-guidance update prepared — **2026-10-16**.
- [x] Final user review of the updated package — approved **2026-10-16**; correctness-first best-practice guidance added at the user's request.
- [ ] GitHub push — authorized **2026-10-16**; publication verification pending. Report drafts and generated results are excluded.
- [ ] Source-data/GIF redistribution terms confirmed — upstream tkoz0 revision contains no stated license, and the user-supplied GIF has no recorded origin. Attribution is included; it does not establish a license.
- [ ] Prism report synchronized — pending.

The report is excluded from this repository package for now. Milestones will be mirrored in the report, but personal assignments will not be duplicated in GitHub documentation or issues.
