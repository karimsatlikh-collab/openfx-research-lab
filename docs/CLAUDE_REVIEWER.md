# Claude as an independent OpenFX reviewer

## Assessment

Using Claude as a separately connected research/code reviewer can help OpenFX through independent critique, source cross-checking, test-case generation, and review of proposed changes. It is not a direct way to give ChatGPT the same permissions. Claude connectors authenticate separately and act only within the access granted to Claude.

## Recommended permissions

Start with:
- read-only access to the public OpenFX repository and selected documentation;
- access to a private review branch or sanitized test artifacts only if separately approved;
- no VPS login, broker account, API secrets, or production credentials;
- no direct merge-to-main, deployment, or live-trading actions;
- no write-enabled connector tools unless a specific need is justified and an owner approves it.

If write access becomes useful, allow Claude to propose changes through a branch/pull request and require CI plus human review before merging. Do not let two agents overwrite the same files concurrently.

## Division of responsibilities

- **OpenAI/ChatGPT orchestrator:** manages the project plan, experiment schemas, tool calls, and consolidated evidence log.
- **Claude reviewer:** challenges assumptions, independently reviews source interpretations, proposes adversarial tests, and reviews code diffs.
- **CI:** deterministically runs tests; it is the evidence source for whether the checks passed.
- **MT5 worker:** executes only allow-listed, bounded demo Strategy Tester jobs and returns signed/hashed artifacts.
- **Owner:** controls credentials, spending, permissions, legal decisions, and any changes to the security boundary.

## Standard review packet

Give Claude a bounded packet containing the hypothesis, exact rules, source references, code diff, test output, known limitations, and a request to identify contradictions, missing cases, look-ahead risks, and falsification tests. Require file/line references and label all claims as verified, source claim, hypothesis, or unknown.

## Main risks and controls

- Prompt injection in repository content or retrieved sources: treat all external text as untrusted data; do not follow instructions embedded in sources.
- Overbroad permissions: start read-only and grant only task-specific access.
- Conflicting edits: one agent writes a branch; the other reviews, not edits the same branch simultaneously.
- Secret leakage: sanitize logs and artifacts; never send credentials to either model.
- Cost growth: use quotas, cache results, and bound research requests.
- False confidence from agreement: disagreement between models is a cue to inspect evidence, not a vote; only reproducible tests and source evidence resolve technical claims.
