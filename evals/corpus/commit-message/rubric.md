1. COMMIT_MSG.txt exists and is non-empty.
2. Subject line is <= 72 characters and states the user-visible fix (expired
   refresh tokens accepted), not the implementation detail.
3. Body explains the root cause (clock-skew allowance applied twice) in <= 4
   sentences.
4. Mentions the regression test.
5. No bullet lists in the subject; no "various fixes"-style vagueness anywhere.
