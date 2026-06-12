# Contributing to wiki-translate

Thanks for your interest. A few guidelines.

## Scope

We welcome contributions that:

- Improve translation quality (better prompts, structured wiki markup preservation, glossary support)
- Expand language coverage beyond English ↔ Chinese
- Strengthen the review-assistance features (better hallucination detection, source verification, claim extraction)
- Improve the CC BY-SA attribution output to match Wikipedia community conventions
- Add adapters for additional agent platforms (Codex CLI, etc.)
- Improve test coverage and documentation

## Out of Scope

The following will not be accepted as PRs:

1. **Automated publishing to Wikipedia.** This tool is designed to produce drafts for human review. We will not add any code path that writes to the Wikipedia edit API, even behind a flag, even with consent prompts. This is a deliberate design constraint — see the README disclaimer for the reasoning.
2. **Removal of the DRAFT banner, `{{LLM-assisted translation}}` template, or CC BY-SA attribution generation.** These are required by Wikipedia policy and CC BY-SA license terms.
3. **Removal or weakening of the README disclaimer.**

If you have an idea that you think is on the boundary, please open an issue first to discuss before sending a PR.

## Code of Conduct

By contributing, you agree to follow the [Contributor Covenant](CODE_OF_CONDUCT.md).

## Development

```bash
git clone https://github.com/lch99310/wikipedia-translation
cd wikipedia-translation
pip install -e ".[dev,anthropic]"
pytest
```

## Pull Request Process

1. Fork and create a feature branch
2. Add or update tests
3. Run `pytest` locally
4. Open a PR with a clear description of motivation and changes
