Write a Python script `rotate.py` in the current directory that rotates a JSONL
log file in place: `python3 rotate.py <path> <N>` keeps only the last N valid
JSON lines of the file (silently dropping malformed lines), preserving order.
It must handle a missing file by exiting 0 and creating nothing, and must not
load files via shell commands — pure Python stdlib only.
