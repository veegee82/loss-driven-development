# Rubric — using-ldd trace visualization (3 scenarios)

Four binary visualization-correctness items, scored **per scenario**. Each item: `0` = satisfied in the response, `1` = violated.

The rubric is intentionally narrow — it measures whether the four normative visualization channels introduced in v0.5.0 are emitted and self-consistent. It does NOT score the rest of the trace block (header, loss values, close section) — those are covered by the pre-existing v0.3.0+ trace discipline and are not the θ parameters this release moves.

## Items (apply to every scenario)

1. **Trajectory sparkline present.** The response contains a single-line trajectory visualization built from at least two of the Unicode block characters `▁▂▃▄▅▆▇█` (or the zero-marker `·`), positioned inside the trace block — typically on a `Trajectory:` line, adjacent to the per-iteration numeric list. A plain text arrow-chain `0.500 → 0.375 → …` alone fails this item; the per-iteration visual magnitude channel must be present as block-height glyphs, not as prose.

2. **Mini ASCII loss-curve chart present.** The response contains a multi-line chart inside the trace block with all three structural pieces: (a) ≥ 2 y-axis tick rows each showing a numeric label and a vertical tick marker (`┤`, `│`, or `|`), (b) a horizontal x-axis line with iteration labels (`i1`, `r2`, `o1`, …) readable left-to-right, (c) ≥ 1 data marker (`●`, `*`, `o`, or similar) placed on the chart body corresponding to an iteration's loss value. A loss table alone, or a sparkline alone, fails — the chart must have axis + labels + markers.

3. **Per-iteration mode+info line present and well-formed.** Every iteration line in the detailed per-iteration section of the trace satisfies BOTH:
   - **Mode indicator**: the label line names the loop AND (where applicable) the mode — one of `(inner, reactive)`, `Phase …(architect, <creativity>)` with `<creativity>` ∈ {standard, conservative, inventive}, `(refine)`, or `(outer)`. A bare `Iteration i1:` with no parenthetical fails.
   - **Info line**: an indented continuation line with a skill reference (usually wrapped in `*<skill-name>*` or named in prose) followed by a one-line description of what concrete action the iteration produced (a fix, a filter, a docstring section, a rubric update — NOT just a restatement of the loss value).

   An iteration that carries only a loss number with no information about what the skill did, OR that omits the mode/creativity parenthetical, fails this item. Rationale: the user needs to audit *what the skill did* per iteration, not just that *some* change happened; without mode+info the trace cannot be walked step-by-step after the fact.

4. **Trend arrow present with correct net-direction semantics.** The sparkline line (or a dedicated trend line) ends with a coarse trend arrow — one of `↓`, `↑`, `→` (or an equivalent single-glyph convention). The arrow reflects the **first-vs-last loss delta**, not a local or majority direction, per the rule:

   ```
   ↓  if (last − first) <  −0.005    (net descent)
   ↑  if (last − first) >  +0.005    (net regression)
   →  if |last − first| ≤ 0.005      (plateau)
   ```

   Scenario 3 is the discriminator: `0.667 → 0.833 → 0.167` → net delta `−0.500` → arrow MUST be `↓`. A response that chooses `↑` because of the local i1→i2 regression, or `→` because of non-monotonicity, fails this item.

## Scoring shape

Per scenario: sum violations (0–4). `Δloss = red_loss − green_loss`.

Pass threshold for v0.5.0:

```
for each scenario:   Δloss ≥ 1
bundle normalized:   mean(Δloss) / 4 ≥ 0.30
```

A scenario with `red_loss = 4` and `green_loss = 4` is flat — the v0.5.0 skill wording did not transfer the visualization discipline through the system message. That is an LDD layer-4/5 failure in the skill itself; diagnose and re-capture, do not ship.

## Why these 4 items and not more

The rubric measures *visualization emission plus per-iteration audit-surface*, not methodology or architecture quality. Each item maps 1-to-1 to a channel v0.5.0 introduces:

| Rubric item | v0.5.0 skill change |
|---|---|
| 1 (sparkline) | Trajectory-line spec in `using-ldd/SKILL.md` § Loss visualization |
| 2 (mini chart) | Mini-chart spec in the same section (y-axis snap, x-axis labels, markers) |
| 3 (mode+info) | Mode-indicator grammar + per-iteration info-line requirement in the same section |
| 4 (trend arrow) | First-vs-last delta arrow-semantics rule in the same section |

A RED response cannot satisfy items 1, 2, 4 by coincidence — base models do not spontaneously emit `▁▂▃▄▅▆▇█` sparklines or `┤`/`●` axis charts or explicit net-direction arrows unless instructed. Item 3 is partially reachable by RED on prompts that themselves contain skill names (RED may echo them back), but the **mode-indicator sub-requirement** (`(inner, reactive)`, `(architect, inventive)`, etc.) is specific to v0.5.0 and does not occur in pre-existing training data.
