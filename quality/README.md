# Quality Cleaner V2

```bash
python -m quality.cleaner web ../site
python -m quality.cleaner app ../application --proposal --output proposed-changes.json
python -m quality.cleaner minecraft ../mod
```

The same standard-library scanner is bundled separately with every installed builder.
It never deletes, moves, rewrites or applies a proposal to project files.

| Analysis | Evidence and limits |
| --- | --- |
| Python unused imports / unreachable code | AST names and control flow; dynamic imports/side effects need review |
| Duplicate code/files / inconsistent naming | Normalized Python function bodies and identical text; intentional duplicates are possible |
| Unreferenced JS/TS files / dependencies | Conservative literal import/HTML/CSS graph; framework entrypoints and dynamic plugins remain uncertain |
| Placeholders, TODO/FIXME, generic text | Heuristics, never proof of AI authorship |
| Source security | Candidate dynamic execution/permission bypass/credential patterns; values omitted, no security certification |
| Missing tests / app API boundaries | Static path/auth/validation markers; trace real middleware and run API tests |
| Web | HTML language, alt/title/viewport checks and visual-pattern candidates; screenshots/axe remain separate |
| Minecraft | JSON, loader entrypoints, local texture references, recipe structure and compatibility markers; game runtime remains separate |

Builds/dependencies/worlds and linked directories are excluded. Resource/assets/migration
content can be inspected but is never treated as disposable by filename. Scans are limited
to 5,000 files, 256 KB per text file and 16 MB of text; skipped files/limits are reported.
Environment files are not read.

`--proposal` generates diffs only for narrowly recognized single-name unused module imports,
with before/after hashes, reasons and reverse-patch rollback instructions. It does not
apply the diff. Review import-time side effects and dynamic use, back up/commit the original,
then separately authorize any changes and rerun the relevant tests. No unused-file or
dependency removal is proposed automatically.
