# Recursive 0.1.2 — initial skills-only submission

This initial submission packages four portable beta workflows from the v0.1.2 release:
Observe, Learn, Verify, and Coordinate. It has no MCP server, app, hooks, authentication,
network connector, or automatic repository setup.

Reviewers can run every evaluator case with Python 3.12 and temporary repositories. The
skills preserve existing project instructions and configuration. Observe and Learn write
only sanitized user-private sidecar state; Coordinate writes only repository-scoped private
sidecar state; Verify is stateless and read-only. Destructive privacy commands remain dry-run
until the user explicitly requests application.
