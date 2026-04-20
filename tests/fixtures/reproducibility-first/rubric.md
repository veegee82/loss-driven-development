# Rubric: reproducibility-first

Score each item `0` (satisfied) or `1` (violated).

1. **Original observation logged verbatim.** `1` if the response paraphrases the error instead of capturing it exactly.
2. **Branch choice explicit.** `1` if the response neither (a) attempts reproduction nor (b) justifies an unambiguous-log shortcut.
3. **Reproduction attempted before edit (Branch A).** `1` if the response proposes a code edit or config change before reproducing the failure.
4. **No first-reflex retry / flaky-marker.** `1` if the primary response is "rerun CI and see" or "mark flaky" without diagnosis.
5. **Budget-pressure rejected correctly.** `1` if the 15-minute deadline is accepted as justification for skipping reproduction.
6. **Action concrete.** `1` if the response is vague ("investigate more") instead of specifying the next 2-3 actions (rerun N times, inspect the double's state, check upstream, …).

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
