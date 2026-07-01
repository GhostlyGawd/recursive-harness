# Agent Mail — Tooling & Capability Needs

When the build needs a tool or capability not currently available, log it here **first**.
Protocol (per the build directive):

1. **Log** the need below (what's blocked, what shape the tool must have).
2. **Search** for an off-the-shelf tool that does it (web research / existing repo deps).
3. **Adapt** an existing tool if one is close.
4. **Build** a minimal one only if nothing fits — and record the decision here.

Bias: the engine stays **stdlib-only** (extractability contract), so a new runtime
*dependency* in `fleet/` is a high bar — prefer a stdlib implementation or a dev-only
(test/CI) tool that the shipped engine doesn't import.

Format:
```
### TOOL-<n> — <capability needed>  [open|found:<tool>|built:<path>|adapted:<tool>]
- Need: <what's blocked and why>
- Shape: <inputs/outputs/constraints the tool must satisfy>
- Search: <what was evaluated>
- Decision: <chosen tool / built artifact / rationale>
```

---

_No tooling gaps logged yet._
