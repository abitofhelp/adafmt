# Release Checklist — AdaFmt

This repo uses **python-semantic-release (PSR)** as the *single source of truth* for versioning, tagging, GitHub Releases, and PyPI publishing. The package version is kept in `pyproject.toml` at `project.version` and is updated by PSR.

> TL;DR: You write conventional commits → CI runs PSR → PSR bumps the version, tags, builds wheels/sdist, publishes to PyPI, and creates the GitHub Release with notes.

---

## 0) One-time sanity (only if things look “off”)

- Ensure the repo has an **anchor tag** (already present: `v0.0.0`). Do **not** hand‑create the next tag — PSR will do that.
- Local Git must see all tags:
  ```bash
  git fetch --tags --prune
  ```
- Confirm PSR sees the next version:
  ```bash
  python -m semantic_release --noop version
  ```
  You should see something like: `The next version is: 1.x.y`.

---

## 1) PreFlight (local, dry‑run & docs refresh)

Run these before opening the release PR.

1. Sync and activate env:
   ```bash
   git checkout main && git pull
   # (optional)
   source ~/.venv/bin/activate  # or your venv
   python -m pip install -U build python-semantic-release
   git fetch --tags --prune
   ```

2. Compute the next version **without writing** (sanity check):
   ```bash
   python -m semantic_release --noop version
   ```

3. Refresh public headers (README + docs) to refer to **the upcoming version** (PSR will write the real value later):
   ```bash
   make docs-headers-next   # idempotent; previews and/or updates versioned headers
   ```

   **IMPORTANT**: Review and update documentation:
   - Check if any new guides need to be added to `docs/guides/index.md`
   - Update the Terminal Colors Guide if color scheme changes
   - Verify all new features are documented in appropriate guides
   - Ensure command-line options are current in the CLI guide

4. **Prepare the Commit Template body** (raw data bundle → LLM summary):
   - Generate the bundle of raw inputs that Claude/ChatGPT will distill:
     ```bash
     make release-body        # writes .tmp/release_body_bundle.txt
     # or to capture to a file explicitly:
     make release-body-file   # writes ./RELEASE_BODY.txt
     ```
   - Open the bundle and run the following prompt with Claude/ChatGPT (paste *as is*):

     **Prompt for LLM (Release Notes Draft):**

     > You are drafting release notes for the AdaFmt project. Use the content in the bundle to produce concise, user‑facing release notes. Apply these rules:
     > 1. Title: `## v<NEXT_VERSION> (<TODAY in ISO date>)` and `_This release is published under the BSD‑3‑Clause License._`
     > 2. Sections in this order (only include present ones): **Features**, **Fixes**, **Refactors**, **Performance**, **Docs**, **Continuous Integration**, **Chore**.
     > 3. In each section, list bullet points. Use imperative mood, 1 line per entry; trim internal noise; prefer user‑impact language.
     > 4. Link each bullet to the commit on GitHub when a hash is present, e.g. [`abcdef1`](https://github.com/abitofhelp/adafmt/commit/abcdef1).
     > 5. Collapse near‑duplicate “cut 1.0.0” type messages into a single line.
     > 6. Do **not** invent features; only summarize from the bundle.
     > 7. Keep to ~8–15 bullets total if possible.
     > 8. End with a **Comparison** link: `**Detailed Changes**: [vPREV...vNEXT](https://github.com/abitofhelp/adafmt/compare/vPREV...vNEXT)`.
     >
     > Output **Markdown only**. No preamble. No closing remarks.

   - Paste the generated Markdown into `COMMIT_TEMPLATE.txt` **between** the markers:
     ```text
     ---8<--- COMMIT BODY START
     ... (paste LLM output here) ...
     ---8<--- COMMIT BODY END
     ```
     Keep the header lines above intact; they are part of the template.

5. Stage and commit **only** docs/template changes (non‑bumping scopes like `docs:` are recommended):
   ```bash
   git add README.md docs/ COMMIT_TEMPLATE.txt
   git commit -m "docs: refresh headers; chore: update release commit template"
   git push
   ```

---

## 2) Create the release PR (feature work already merged)

1. Merge the commit that introduces your new CLI flag using a proper **conventional commit** (e.g., `feat(cli): add --foo flag`).
2. Open a small “Release prep” PR containing the updated docs and `COMMIT_TEMPLATE.txt` from PreFlight.
3. When it merges to `main`, CI will run the **official release** workflow.

---

## 3) Official CI Release (GitHub Actions)

This is automatic on push to `main`:

1. `actions/setup-python` installs **python-semantic-release**.
2. PSR computes the next version from commit history.
3. PSR **updates `pyproject.toml`**, writes `CHANGELOG.md`, **creates a Git tag** `vX.Y.Z`, and **builds** via:
   ```bash
   python -m build
   ```
4. PSR **publishes to PyPI** using `PYPI_TOKEN` and **creates a GitHub Release** using `GH_TOKEN`.
5. Artifacts: sdist and wheel uploaded to PyPI; Release notes appear on GitHub.

> You should never hand‑create tags for normal releases. If you need to fix a bad tag, see “Recovery” below.

---

## 4) Post‑release checks

Run locally, or just click through on GitHub/PyPI.

```bash
# make sure local has the new tag
git fetch --tags --prune
git tag --list | tail -n 5

# verify version resolved by PSR now matches
python -m semantic_release --noop version
```

- **GitHub Release** shows `vX.Y.Z` with notes from `COMMIT_TEMPLATE.txt` and the comparison link.
- **PyPI** project page shows **Version: X.Y.Z** (not 0.0.0). If PyPI shows `0.0.0`, see Recovery.

---

## 5) Recovery / Common pitfalls

- **PyPI shows Version 0.0.0**  
  Cause: an old wheel/sdist was built with `project.version = 0.0.0` and uploaded before PSR wrote the bump.  
  Fix:
  1. Delete the *bad* release from PyPI (if allowed) **or** immediately publish `X.Y.(Z+1)`.
  2. Ensure CI order: PSR must *write version → build → upload*. Our workflow already enforces this.
  3. Re‑run the release (merge a small `chore:` commit if needed).

- **“No release corresponds to tag v0.0.0, can’t upload dists”** in logs  
  This line is informational when no artifact is tied to the anchor tag. It does not block current releases.

- **Want a pre‑release (e.g., 1.1.0‑beta.1)**  
  Use prerelease commits (`feat!` still works for bump logic). Configure the prerelease branch & tag format if needed; otherwise prefer normal releases.

---

## 6) Make targets reference

- `make docs-headers-next` – update README/docs headers to show the *next* version.
- `make release-body` – generate `.tmp/release_body_bundle.txt` for LLM input.
- `make release-body-file` – generate `./RELEASE_BODY.txt` snapshot.
- `make clean-baks` – remove legacy backup files (if any).

---

## 7) Minimal “happy path” (copy/paste)

```bash
git checkout main && git pull && git fetch --tags --prune

# sanity
python -m semantic_release --noop version

# prep notes
make release-body
# paste LLM output into COMMIT_TEMPLATE.txt between markers

# docs + template commit
git add README.md docs/ COMMIT_TEMPLATE.txt
git commit -m "docs: refresh headers; chore: update release commit template"
git push

# merge PR → CI runs → PSR publishes GitHub Release + PyPI
```

---

## Notes

- Keep user‑facing docs in a `docs:` commit to avoid bumping by accident.
- Do not hand‑edit the version in `pyproject.toml`; let PSR own it.
- PSR creates the tag. Do not push tags manually unless you’re performing a hot‑fix recovery with care.
