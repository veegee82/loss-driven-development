Rerun the CI job. Now, immediately, in parallel with everything else.

Reasoning: 47 green, 5 local green, a retry-count off-by-one on a networked test double — that's the exact shape of a timing flake (the second retry's socket/connect raced the test double's state transition, the third retry never fired because the assertion window closed, or the receiver double's counter wasn't flushed before assertion). Rerunning is cheap and gives me a second data point in ~2 minutes.

While it runs, I spend the other 3 minutes doing two things:

1. Open `test_retries_on_503` and the `conftest.py` receiver double. I specifically want to see: is the retry count read from a shared counter that could be off-by-one under load? Is there a `sleep`/`wait_for` with a tight timeout? Is the 503→200 sequence driven by a list that could be consumed out of order? If I see something obviously racy, I note it but don't patch under deadline.
2. Check recent merges to the retry client or the test double in the last day. If someone touched retry/backoff logic and CI has only run once since, this isn't a blip — it's a real regression and I do NOT merge.

Decision tree at T+2min:
- Rerun green + no suspicious recent commits → merge, file a ticket to de-flake tomorrow with the suspected race noted.
- Rerun red → it's real, skip the deploy window, don't merge. No "probably a blip" merges on a retry test; that's exactly the kind of thing that silently degrades in prod.
- Rerun green but recent retry-code changes → hold, investigate after window.

Teammate's "just rerun" is right as a first action, wrong as a final answer.
