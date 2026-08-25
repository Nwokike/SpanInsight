# Changelog

All notable changes to SpanInsight. Formats: Keep-a-Changelog-ish; dates are
release dates.

## [2.0.0] — Verified Intelligence (upcoming)

### Added
- **Verified Agent**: Insight answers are planned, executed, and verified
  against real executed outputs — every answer carries a "Verified" badge,
  exact key figures, and honest gap reporting when partial.
- **Findings Memory**: per-project memory of verified insights; Home shows
  "What we know", and all AI prompts inherit past findings as facts.
- **Data Briefs**: one-tap compilation of verified/pinned analysis into a
  shareable report + standalone HTML export for browser print-to-PDF.
- **Quick Import** (FAB): import from a public URL (fetched on the VM) or
  pasted CSV/JSON text.
- **Forms live editing with smart merge**: edit published forms in place;
  kept questions preserve responses, removed ones purge instantly; share
  link unchanged. Includes a truth-based confirmation dialog.
- **Analyze-in-Notebook**: form responses load as a first-class CSV dataset
  with parquet snapshots and auto-refresh of new submissions on return.
- Survey template gallery; interstitial ads at natural completion points
  (session start, autopilot finish, form publish/update) with cooldown.
- python-calamine auto-installed per Colab VM — large Excel files now load
  (verified on a 558k-row workbook) with parquet snapshot reloads.
- Windows and Linux desktop builds alongside Android.

### Changed
- Insight runs show a live plan → execute → verify progress pill; project
  dropdown moved to the end of the Analysis header.
- One persistent kernel websocket per session; concurrent dataset-overview AI
  calls; throttled upload progress — substantially faster imports and cells.
- Offline first-run shows a retry screen instead of trapping users mid-auth;
  app resume re-validates the Colab session automatically.
- Update prompts target 2.0.0 via the gateway version endpoint.

## [1.2.3] — Local Dataset Caching — 2026-06-14
### Added
- Auto-cache on import; seamless recipe replay on reload; smart 7-day cache
  expiry; one cache per project.
### Changed
- "Import Different Dataset" button; clearer missing-dataset banner.

## [1.2.2] — Expert Mode Terminal — 2026-06-06
### Added
- Reusable code terminal shared between View Code and Expert Mode; expert
  toggle with VS Code-style terminal and direct raw-Python execution.
### Changed
- Credit-consistent dialogs when credits are depleted.

## [1.2.1] — Report Editor Layout — 2026-06-05
### Changed
- Cleaner Report Editor action flow; standardized refresh button styling.
### Fixed
- Empty-Reports "Start Analysis" navigation dead-end.

## [1.2.0] — UI/UX Refactoring — 2026-06-04
### Changed
- Forms dashboard alignment; onboarding SafeAreas; standardized action
  buttons; Android-optimized CI; local font packaging.

## [1.1.0] — Security & Performance — 2026-05-26
### Security
- Sandbox builtins restricted; seed phrases masked; parameterized SQL;
  corrupt-JSON recovery.
### Performance
- 95% AI prompt compression; faster suggestions; 10x data preview; sandbox
  thread watchdog.
### Fixed
- Regex variable-width lookbehind crash; clipboard API pattern; background
  sync error handling.

## [1.0.0] — Initial Release — 2026-05-12
- Natural-language data analysis, Autopilot, charts, pinning to reports,
  smart forms with public links, report editor with PDF/Word/PowerPoint
  export, workspaces with recovery phrases, 50 free daily credits.
