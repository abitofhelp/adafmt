# Release Checklist & Tips

This repository uses **python-semantic-release (PSR)** as the source of truth for versioning and publishing.
Documentation headers in `README.md` and under `docs/**` are updated *before* the release using the next computed version.

## Local Preflight (Dry Run)

1. Ensure you're on `main` and up to date:
   ```bash
   git checkout main && git pull
   ```

2. (Optional) Activate your virtual environment.

3. Preview what headers would change (no writes):
   ```bash
   make docs-bump-headers-dry
   ```

4. Apply header updates and create a non-bumping docs commit if needed:
   ```bash
   make docs-bump-headers
   ```
   Notes:
   - The updater runs with `--no-backup` by default (no `.bak` files).
   - The commit message is `docs: update headers for vX.Y.Z` and does not affect the version bump.

## Real Release (CI Authoritative)

1. Merge or push to `main`.

2. GitHub Actions will automatically:
   - Compute the next version with `python -m semantic_release --noop version --print`.
   - Run `scripts/update_doc_headers.py --write --no-backup` with `SEMVER_NEXT` set.
   - Commit and push a `docs:` change if files changed.
   - Run `python -m semantic_release publish` to bump version, tag, generate changelog, build, and publish to PyPI & GitHub Releases.

3. Verify the results:
   - Tag `vX.Y.Z` exists on GitHub.
   - GitHub Release page shows the new release.
   - PyPI lists the new version (if configured).

## Useful One-Offs

- Print next version locally:
  ```bash
  make print-next-version
  ```

- Run the updater with an explicit version (no detection):
  ```bash
  SEMVER_NEXT=1.2.3 python scripts/update_doc_headers.py --write --no-backup
  ```

- Clean any legacy backup files (not produced by default now):
  ```bash
  make clean-baks
  ```

## Tips

- Keep the docs update in a separate `docs:` commit. It’s non-bumping under conventional commits.
- Always let CI be the single source of truth for release versioning.
- If computing the next version fails locally, ensure `python-semantic-release` is installed in your environment:
  ```bash
  python -m pip install "python-semantic-release>=9,<10"
  ```
