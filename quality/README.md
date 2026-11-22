# Quality Cleaner

Each builder can use the same **read-only** analysis engine with its own rules.

```bash
python3 -m quality.cleaner web ./my-website
python3 -m quality.cleaner app ./my-application
python3 -m quality.cleaner minecraft ./my-mod
```

Findings are heuristic review candidates, **not** reliable proof of AI-generated code or unnecessary files. The scanner never deletes files. Temporary artifacts may still contain valuable user data; review each suggestion before removing anything. Protected directories include migrations, resources, Minecraft world data, Git metadata, build and dependency directories.

Future versions should add reference-aware unused-file analysis, AST-based duplicate detection, visual review, configurable policies, an explicit approval UI, and rollback. These are not yet implemented.
