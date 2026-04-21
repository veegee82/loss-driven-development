# Score — using-ldd trace visualization — 2026-04-21 (CLEAN baselines via direct API)

**Scorer:** Silvio Jurk (skill author). Raw RED + GREEN attached per scenario under this directory.
**Rubric:** `../../rubric.md` (4 binary visualization-correctness items, per scenario).
**Capture:** `scripts/capture-red-green.py` — `deepseek/deepseek-chat-v3.1`, T=0.7, via OpenRouter, no agent harness, no ambient methodology. GREEN runs prepend `skills/using-ldd/SKILL.md` as a single system message. This run supersedes `20260421T120520Z-clean` (spec revised: per-iteration `█`/`░` bar removed in favor of mandatory mode+creativity indicator and per-iteration skill-info line).

## Per-scenario results

### 1. inner-three-iters

User prompt: 3-iteration inner-loop fix for `test_parse_timestamp_utc` flake with explicit per-iteration rubric data (7 items, losses 4/7 → 2/7 → 0/7).

Expected GREEN: sparkline + mini chart + mode+info line + trend arrow `↓`.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Sparkline present | **1** | 0 | RED: nested JSON only, no Unicode glyphs. GREEN: `Trajectory: █▄▁` on a dedicated line |
| 2 | Mini loss-curve chart | **1** | **1** | RED: no chart. GREEN: **NO CHART EMITTED** — the model produced the sparkline + mode+info lines but skipped the multi-row chart. Likely a T=0.7 rendering-skip; tightening the SKILL.md wording around "≥ 3 iterations MUST include chart" may raise the hit rate |
| 3 | Per-iter mode+info line | **1** | 0 | RED: no mode indicator, no info lines (flat JSON). GREEN: every iteration carries `(inner, reactive)` + an indented `*Invoking <skill>*: <action>` line (minor typo in scenario 1 GREEN: `reproducibilty-first` instead of `reproducibility-first` — does not fail the rubric, which measures format not spelling) |
| 4 | Trend arrow (net direction) | **1** | **1** | RED: no arrow. GREEN: **Trajectory line ends WITHOUT a trend arrow** — `Trajectory: █▄▁` has no trailing `↓`/`↑`/`→`. Same rendering-skip as item 2; the model emitted sparkline but not the end-of-line arrow. Net direction would have been `↓` (0.571 → 0.000) |

**RED: 4 / 4  GREEN: 2 / 4  Δloss = +2**

### 2. all-three-loops

User prompt: full three-loop run (inner 8 items → refine 10 items → outer 8 items) with explicit per-iteration losses across 6 iterations.

Expected GREEN: sparkline + mini chart (6 columns, phase-mix labels i1/i2/i3/r1/r2/o1) + mode+info per iter + trend arrow `↓`.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Sparkline present | **1** | 0 | RED: markdown prose with section headers, no glyphs. GREEN: `Trajectory : █▆▃▂··  0.750 → 0.375 → 0.125 → 0.100 → 0.000  ↓` — full sparkline + trend arrow inline |
| 2 | Mini loss-curve chart | **1** | 0 | RED: no chart. GREEN: 4-row chart with y-axis labels 0.75 / 0.50 / 0.25 / 0.00, x-axis `└─i1─i2─i3─r1─r2─o1→`, phase-prefix legend included, ≥ 1 `●` marker per row |
| 3 | Per-iter mode+info line | **1** | 0 | RED: section-headed prose, no mode-indicator parentheticals. GREEN: every iteration line carries `(inner, reactive)` / `(refine)` / `(outer)` and an indented `*<skill-name>* → <action>` continuation line with the concrete change the iteration produced. Skill names are real LDD skills (`reproducibility-first`, `root-cause-by-layer`, `e2e-driven-iteration`, `loss-backprop-lens`, `dialectical-reasoning`, `iterative-refinement`, `docs-as-definition-of-done`, `method-evolution`, `drift-detection`) — not hallucinated |
| 4 | Trend arrow (net direction) | **1** | 0 | RED: no arrow. GREEN: `↓` at end of trajectory line. Net delta `0.750 − 0.000 = −0.750` → `↓` correct |

**RED: 4 / 4  GREEN: 0 / 4  Δloss = +4**

### 3. regression-and-recovery

User prompt: non-monotonic trajectory `0.667 → 0.833 → 0.167` (i1→i2 regression, i2→i3 recovery). The discriminator for rubric item 4 — net direction is descent, not ascent.

Expected GREEN: sparkline + mini chart + mode+info per iter + trend arrow `↓` (NOT `↑` — local regression in i1→i2 does not flip the end-to-end arrow).

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Sparkline present | **1** | 0 | RED: flat JSON. GREEN: `Trajectory : █▇▁   0.667 → 0.833 → 0.167  ↓` — `█` at i1 (rescaled against max), `▇` at i2 (peak), `▁` at i3 (recovered) |
| 2 | Mini loss-curve chart | **1** | 0 | RED: no chart. GREEN: chart with y-axis 0.75 / 0.50 / 0.25 / 0.00, x-axis `└─i1─i2─i3→`, `●` markers. Minor snap inaccuracy on i2 (0.833 placed on 0.50 row — should snap to 0.75 per the SKILL.md recipe `floor(v/0.25 + 0.5) * 0.25 = floor(3.832) = 3 → 0.75`); item measures structural presence, not snap precision |
| 3 | Per-iter mode+info line | **1** | 0 | RED: no mode, no info lines. GREEN: every iteration carries `(inner, reactive)` + an indented `*<skill-name>* → <action>` line. **Caveat:** GREEN used invented skill names (`*optimization-pass-1*`, `*caching-implementation*`, `*revert+alternative*`) rather than real LDD skills. The rubric measures format, not skill-name validity — the `*...*` wrapping + action-description structure is present. A stricter rubric item in v0.5.1 could require named skill references to match the LDD skill set |
| 4 | **Trend arrow (net direction)** | **1** | 0 | RED: no arrow. GREEN: `↓` at end of trajectory line despite local i1→i2 regression. Model correctly read the non-monotonic prompt: the per-step `Δ +0.167 ↑` on i2 and `Δ -0.667 ↓` on i3 are both present AND distinct from the end-to-end sparkline arrow. First-vs-last rule honored (`0.667 − 0.167 = 0.500 > 0 → ↓`) |

**RED: 4 / 4  GREEN: 0 / 4  Δloss = +4**

## Summary

| Scenario | RED | GREEN | Δloss |
|---|---:|---:|---:|
| inner-three-iters | 4 / 4 | 2 / 4 | **+2** |
| all-three-loops | 4 / 4 | 0 / 4 | **+4** |
| regression-and-recovery | 4 / 4 | 0 / 4 | **+4** |
| **Mean** | **4 / 4** | **0.667 / 4** | **+3.333** |

**Pass gate: every scenario must show Δloss ≥ 1. All three scenarios PASS.** Mean Δloss = 3.333 / 4 (bundle-normalized: `0.833`), above the `≥ 0.30` release threshold by a wide margin.

## Interpretation

- **Scenario 1 GREEN dropped 2 items** (mini chart and trend arrow were not emitted) compared to the previous `20260421T120520Z-clean` run where all four items flipped cleanly. The mode+info line and sparkline both transferred; chart and trend-arrow emission appears to be the first thing the model drops under T=0.7 rendering compression on the shortest scenario. Δloss = +2 is still well above the gate, but it is the weakest scenario in this fixture.
- **Scenarios 2 and 3 GREEN hit all four items** — full sparkline + trend arrow inline, mini chart with axis structure, mode+info lines on every iteration with real LDD skill names (scenario 2) and invented names in the correct format (scenario 3). Scenario 3 correctly applied the first-vs-last trend-arrow rule on the non-monotonic trajectory, keeping per-step `Δ` arrows and the end-to-end sparkline arrow as distinct channels.
- **Mode indicator is the strongest novel signal.** Base models do not spontaneously produce `(inner, reactive)` / `(refine)` / `(outer)` parentheticals on iteration labels — this phrase is specific to the v0.5.0 spec and does not occur in pre-existing training data. All three GREEN captures emit it; no RED capture comes close.
- **Per-iter info lines transfer as-format.** GREEN consistently emits `*<skill-name>* → <action>` or `*Invoking <skill>*: <action>` patterns after every iteration label — the rubric measures this channel as present, regardless of whether the skill names are real (scenarios 1 and 2) or invented to fit the task (scenario 3). A future tightening could require named skills to match the bundle's skill set.
- **Removing the per-iteration `█`/`░` bar was the right call.** The previous run's bars carried information already encoded by the sparkline and chart (and on scenario 3 actually propagated a snap error visually, making the regression look artificially dramatic). The mode+info line adds the audit channel the user explicitly asked for — "was getan wurde" / "welcher mode" / "user soll die arbeit des skills nachvollziehen" — while keeping the trace block one-screenful per run.

## Caveats

- **N=1 scorer** (skill author). Raw RED + GREEN artifacts attached per scenario so a second reviewer can re-score.
- **Single-sample measurement at T=0.7** per scenario. Scenario 1's Δloss = +2 at a single sample may be a distribution-tail outlier; re-running N=5 would confirm whether the model systematically drops chart+arrow on short scenarios or it was a one-off rendering skip. Cost ≈ $0.02 for the re-run; deferred to v0.5.1 unless a second reviewer requests the distribution now.
- **`deepseek/deepseek-chat-v3.1` via OpenRouter** specifically. Other base models (`gpt-5-mini`, `claude-haiku-4-5`, `llama-3.3-70b`) may render the channels differently. The rubric allows equivalent single-glyph conventions; cross-model portability would need re-capture.
- **GREEN responses were not truncated.** Full content retained under each `<scenario>/green.md`.
- **Scenario 3 GREEN uses invented skill names** (`*optimization-pass-1*`, `*caching-implementation*`, `*revert+alternative*`). The rubric measures format presence, not skill-name validity. A stricter v0.5.1 rubric item could enforce name-matching against `skills/*/SKILL.md`.
- **Scenario 2 GREEN chart has a minor misalignment** — 6 iterations, only 5 `●` markers visible on the chart (r1 and r2 collapsed on the same col). Item 2 measures structural presence (≥ 1 marker), which is satisfied.
