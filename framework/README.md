# Shared routing layer

`registry.json` declares domain names, skill paths and keyword hints.

`route.py` selects domain-specific entrypoints using deterministic keyword matching and adds the existing workflow orchestrator for cross-domain requests. It does not fetch data, invoke models, run tools, execute commands from a task, or guarantee correct skill selection.

Example:

```bash
python3 framework/route.py "Build a minecraft fabric mod with a backend api"
python3 -m unittest discover -s tests -v
```

The router is deliberately simple and auditable. Future versions may add explicit dependencies, conflicts, typed handoffs, and real agent integrations after tests and permission controls are designed.
