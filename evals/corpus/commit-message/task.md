Here is a diff summary: a fix to the auth middleware where expired refresh
tokens were accepted for 60 extra seconds due to a clock-skew allowance being
applied twice (once in validate(), once in refresh()); the fix removes the
allowance from refresh() and adds a regression test.

Write the git commit message for this change to a file named COMMIT_MSG.txt
in the current directory. Follow standard commit conventions: keep the subject
line within 72 characters and focused on the user-visible effect of the fix (what
changes for users); the body explains the underlying mechanism / root cause and
notes the regression test.
