Quick fix - strip matching surrounding quotes after the lowercase/strip:

```python
 def parse_user_input(raw: str) -> str:
     if raw is None:
         return ""
     s = raw.lower().strip()
     if not s:
         return ""
+    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
+        s = s[1:-1]
     return s
```

That makes `test_parse_handles_quotes` pass. Checks length >= 2 so a lone `"` doesn't blow up, checks first and last char match so `"hello` (unbalanced) stays as-is, handles both single and double quotes.

Heads up though - looking at the commit log and that pattern list (200-char trim, HTML escape, NFKC, trailing punctuation), you're going to be back here 4 more times with 4 more 3-line patches. At some point it's probably worth just writing the whole pipeline in one go rather than another round of whack-a-mole, but that's a tomorrow problem. For right now, ship the two-line fix and get the test green.
