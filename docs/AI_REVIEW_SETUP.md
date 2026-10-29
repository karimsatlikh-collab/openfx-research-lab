# Enable AI review with Gemini

This is an optional, bounded first step toward AI-assisted OpenFX work. It does not connect Claude, does not run MT5, and does not execute generated code.

## What it does

- Automatically reviews pull-request diffs opened from branches in this same repository.
- Writes findings to the GitHub Actions run summary.
- Can also run a research-methodology review manually through Actions → AI review (Gemini) → Run workflow.
- Uses the Gemini API, so free usage is subject to Google's current model availability, rate limits, and quota. It is not unlimited.
- Does not post comments, approve PRs, merge changes, run shell commands from the PR, or access broker/MT5 credentials.

## One-time setup required from the repository owner

1. Open Google AI Studio: https://aistudio.google.com/
2. Create a Gemini API key under the account you intend to use. Check the current API terms, regional availability, and free-tier quota before relying on it.
3. In the GitHub repository, open Settings → Secrets and variables → Actions → New repository secret.
4. Set the secret name to exactly GEMINI_API_KEY and paste the key as its value. Never put the key in a file, issue, prompt, commit, or screenshot.
5. Open Actions and confirm that workflows are enabled.
6. Open Actions → AI review (Gemini) and run a manual test. For a research review, optionally enter a question. Review the output under the run's Summary tab.

## Security boundaries

- The automatic PR workflow uses pull_request_target so the workflow definition comes from the trusted base branch, but it never checks out or executes PR code.
- Automatic review is limited to PRs whose head branch is in this same repository; fork PRs are skipped.
- The workflow has read-only repository permissions and sends the diff or research question to Google's Gemini API.
- Treat AI findings as suggestions, not verified facts. Independently verify important claims and run tests.
- If the key is unavailable, the free quota is exhausted, or Google blocks access in the current region, the review will fail; no bypass is built in.
- Claude is not automatically connected by this workflow. A separate Claude API/authorized integration would require its own credentials, availability checks, and potentially paid usage.

## Known limits

This first version reviews one PR diff (truncated at 45,000 characters) or one research question. It does not continuously monitor the repository in the background, and it does not provide unattended Claude reviews. Do not interpret a green workflow as proof that code is correct or a strategy is profitable.
