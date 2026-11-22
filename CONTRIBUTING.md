# Contributing

Thanks for improving these skills.

1. Open an issue describing the problem and expected behavior for substantial changes.
2. Keep each pull request focused. Include a reproducible synthetic example.
3. Run `python3 scripts/validate_skills.py` and `python3 -m unittest discover -s tests -v`.
4. Do not upload secrets, customer information, personal data, internal source code, or copyrighted content without permission.
5. Describe limitations and avoid claims of guaranteed security or correctness.

## Skill format

Create `skills/<slug>/SKILL.md` with YAML frontmatter containing `name` and `description`, then include sections titled `When to use`, `Procedure`, and `Output`. Use only lowercase letters, digits and hyphens in directory names.

By contributing, you agree that your contributions are licensed under the MIT license in this repository.
