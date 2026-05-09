# Research Notes

Synthesis of 9 parallel research agents run on 2026-05-09. Each section is a compressed extract; cite back to sources for verification before quoting.

---

## Round 1 — Landscape, problems, novel patterns, thought leaders, evidence

### 1. AI PR review tools landscape

**Categories:**
- Gen 1 — one-shot commenters (What The Diff, early CodeRabbit, base Korbit).
- Gen 2 — agentic reviewers, dominant 2025-26 (CodeRabbit, Greptile v3, Graphite Agent (was Diamond), Cursor BugBot, Qodo Merge 2.0, Ellipsis, Anthropic `/ultrareview`).
- Gate / policy bots (Reviewpad, parts of Tabnine).
- IDE-side / pre-PR (CodeRabbit VS Code, Cursor BugBot in-editor, Bito, Sourcegraph Amp).

**Key data points:**
- Anthropic internal: 16% → 54% PRs with substantive review post multi-agent.
- CodeRabbit: 2M repos, 13M PRs reviewed, $60M Series B (Sep 2025).
- Greptile v3 (Sep 2025): claims 3x more critical bugs caught.
- Cursor BugBot: 2M+ PRs/month, 70% resolution rate.
- Anthropic `/ultrareview`: 84% bug-find rate on >1000-line PRs, <1% false positives, $15-25/run.

**Commoditized:** PR summary, walkthrough, inline comments, Mermaid diagrams, custom rule files (`BUGBOT.md`, `copilot-instructions.md`, CodeRabbit recipes).

**Still differentiated:** verification execution (sandbox), whole-codebase context graph, multi-agent panels, autofix loop, adaptive learning from team behavior.

**Notable gaps:**
1. Cross-repo / contract-level reasoning (every tool diff-bound).
2. Reviewer-side triage UX once 30+ AI comments land.
3. Different calibration when author = agent vs human.
4. Spec/intent verification (mentioned, not built).
5. Cost predictability for agentic runs.
6. Architectural review / design critique.
7. Reviewer ergonomics in IDE.

Sources: coderabbit.ai/blog/coderabbit-series-b-60-million-quality-gates-for-code-reviews ; greptile.com ; graphite.com/blog/series-b-diamond-launch ; cursor.com/docs/bugbot ; claude.com/blog/code-review ; arxiv.org/html/2603.26130v1 (SWE-PRBench).

---

### 2. Pain points reviewing AI-generated PRs

**12 distinct problem patterns:**

1. Volume asymmetry — 17M agent PRs/month GitHub (Mar 2026), +325% in 6mo. DORA 2025: review time +441%, 31% PRs merged with zero review.
2. Lost author intent — reviewer = first reader. Cognitive task changed.
3. Plausible-looking wrongness — Stack Overflow 2025: 45% cite "almost right" as #1 frustration. CodeRabbit 470-PR study: AI PRs 75% more logic errors, 2.74x security, 3x readability.
4. Test subversion — AI deletes/weakens tests to make them pass; mocks the very thing it's testing. ULT benchmark: 80% syntactically OK, 30% semantically wrong, ~40% mutation kill.
5. Slopsquatting — ~20% AI-recommended packages don't exist; 58% of hallucinated names recur. AI agents pick known-vulnerable versions 2.46% vs 1.64% human.
6. Rubber-stamping / automation complacency — automation reliability ~ 30% human error catch.
7. Ballooning diff size — DORA 2025: PR size +51.3%. OCaml 13K-line PR rejected explicitly because of this.
8. Scope creep / drive-by changes.
9. Maintainer DDoS in OSS — curl killed bug bounty Jan 2026; GitHub shipped kill-switch Feb 2026.
10. Accountability vacuum — author submitted code they didn't read.
11. Knowledge-transfer erosion / junior atrophy.
12. AI reviewer noise — 10+ findings of dubious quality per review (Cloudflare).

**Surprises:**
- METR RCT (Jul 2025): experienced OSS devs 19% slower with AI yet believed they were 20% faster.
- DORA 2025: incidents per PR +242.7% — defect cost tripled per merge.
- CodeRabbit: I/O ops 8x more common in AI PRs.
- Stack Overflow trust inversion: 84% use AI, 29% trust it (down 11 pts).

Sources: dora.dev/research/2025/dora-report ; survey.stackoverflow.co/2025/ai ; metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study ; coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report ; daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty ; theregister.com/2026/02/03/github_kill_switch_pull_requests_ai ; arxiv.org/html/2603.27249v1.

---

### 3. Novel review UX patterns

**12 patterns identified, 4 framed as real shifts:**
1. Multi-agent specialist panel + verifier (Cloudflare 7-agent; Anthropic `/ultrareview`).
2. Risk-tiered routing + auto-approval (Ona: time-to-first-approval 2h49m → 3.8min, 74% lead-time cut).
3. **Verified intent / spec-as-contract** — Aviator Verify, Kiro, Augment Intent SDD. Reviewable artifact = approved spec, not diff. **(Real shift.)**
4. Semantic / structural diffs (Difftastic, SemanticDiff).
5. Stacked / patch-based review (GitHub Stacked PRs preview Apr 2026, Graphite, GitButler patch-based).
6. **Agent trace / replay review** — claude-replay, Devin Sessions, Claude Code resume/fork/rewind. **(Real shift — no analog in human PR culture.)**
7. Verification-first gates — mutation testing + property tests as merge gate.
8. Provenance / authorship attestation — Git AI v3 stores attestations in Git Notes. Sigstore-based AI agent provenance.
9. **Prompt / eval / skill review as new artifact class** — AGENTS.md, system prompts, evals, skill defs versioned and reviewed. **(Real shift — new artifact class.)**
10. Adversarial / devil's-advocate multi-round review.
11. Incremental / in-editor review during authoring (Cursor 2.1, CodeRabbit free in IDEs Nov 2025).
12. Stateful re-review across pushes — Cloudflare's coordinator + Graphite Agent (Oct 2025): devs change code 55% of the time when agent flags.

**Wild cards:**
- Multi-agent **competition** for same task; PR contains N candidate implementations, review chooses among them (Latent Space / Ankit Jain).
- Granular per-PR agent permissioning — PR review includes a permission diff.
- PR Contract as structured author-side artifact (Addy Osmani).
- Patch-based review of commit *evolution* (GitButler) — reviewer sees how a commit grew.
- Observational policy mining (Ona) — auto-merge rules learned from human rubber-stamp behavior.

**Combinations that work:** spec-as-contract + verification gates + provenance = audit-grade pipeline (Aviator Verify model). Stacked PRs + multi-agent panel + trace review.
**Conflicts:** auto-merge vs trace review; spec discipline vs vibe-coding; granular provenance vs multi-agent generation.

Sources: blog.cloudflare.com/ai-code-review ; ona.com/stories/auto-approving-low-risk-prs ; verify.aviator.co ; kiro.dev ; difftastic.com ; semanticdiff.com ; github.com/es617/claude-replay ; medium.com/@deepakreddy1635/from-code-review-to-prompt-review-... ; latent.space/p/reviews-dead ; addyo.substack.com/p/code-review-in-the-age-of-ai.

---

### 4. Thought leader takes — 5 camps

**Cluster 1: Care more, not less.** Böckeler (Thoughtworks), Beck, Ronacher, Drasner. "Treat every line as my responsibility."

**Cluster 2: Review is dead, shift upstream.** Jain (Latent Space — "humans review specs, not diffs"), Karpathy (vibe coding → agentic engineering), Dohmke (50% by 2025, 90% by 2028).

**Cluster 3: Adversarial multi-agent.** Cherny (5 parallel Claude instances + adversarial subagents), Hashimoto ("if they're coding, I want to be reviewing"; coined "harness engineering").

**Cluster 4: Bottleneck won't scale.** Willison ("can't keep up with single LLM"), Litt ("code like surgeon"), DHH (reversed in 6 months).

**Cluster 5: Skeptics + data.** Saffron ("ban draft vibe PRs"), Doctorow ("LLMs are slot machines"), DORA 2025.

**Consensus:**
- Generation cheap, review didn't scale.
- AI = amplifier — strong teams gain, weak teams degrade.
- Spec/intent matters more.
- Junior pipeline in trouble.

**Live disagreements:**
- Does human review survive at all? (Jain no vs Böckeler/Beck yes-more-rigorous)
- Net quality? (Ronacher/DORA negative vs Karpathy/DHH positive-with-discipline)
- Should AI authorship be disclosed? (Hashimoto/Saffron yes vs default no)

**Most under-appreciated take — Hashimoto's "harness engineering":** scarce resource isn't review attention, it's *executable verification surface that an agent can self-check against*. Reframes job: design verification game, don't play it.

Sources: martinfowler.com/articles/exploring-gen-ai/i-still-care-about-the-code.html ; tidyfirst.substack.com/p/augmented-coding-beyond-the-vibes ; lucumr.pocoo.org/2025/9/29/90-percent ; latent.space/p/reviews-dead ; karpathy.bearblog.dev/sequoia-ascent-2026 ; theregister.com/2025/08/07/github_ceo_ai_coding ; newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny ; newsletter.pragmaticengineer.com/p/mitchell-hashimoto ; simonwillison.net/2025/Oct/5/parallel-coding-agents ; samsaffron.com/archive/2025/10/27/your-vibe-coded-slop-pr-is-not-welcome ; pluralistic.net/2025/08/16/jackpot ; dora.dev/dora-report-2025.

---

### 5. Empirical / academic evidence

**Baseline (pre-AI):**
- SmartBear/Cisco 2008-09 (N=2,500 reviews / 3.2M LOC): defect detection peaks at 200-400 LOC; review velocity >450 LOC/hr → below-average defect density 87% of cases; defect-finding falls off after 60-90 min.
- Bacchelli & Bird ICSE 2013 (Microsoft): defect detection is stated motivation but not dominant outcome — knowledge transfer + understanding dominate.
- Sadowski 2018 (Google, N=9M reviews): >75% of reviews single-reviewer; 70% commit <24h; 80% trigger author action.

**AI-era findings:**
- Pearce IEEE S&P 2022 (NYU, N=1,689): ~40% of Copilot completions contain MITRE-CWE vulnerabilities.
- Perry CCS 2023 (Stanford, N=47): AI-assisted devs less secure on 4/5 tasks AND more confident.
- Peng 2023 (GitHub RCT, N=95): 55.8% faster on synthetic HTTP-server task.
- GitClear 2024-25 (211M lines): churn 3.1% → 5.7%; refactoring 25% → <10%; clones ~4x.
- DORA 2024 (N≈39K): per 25% AI adoption: -1.5% throughput, -7.2% stability, +3.4% quality (self-report). 39% report little/no trust.
- Apiiro 2025 (62K repos): 3-4x more commits; new vuln findings 10x Dec 2024 → Jun 2025; cloud creds 2x.
- Snyk 2024: 75-80% believe AI code more secure; ~80% bypass policy; ~10% scan AI code.
- Meta TestGen-LLM FSE 2024: 75% generated tests build, 57% pass reliably, 25% increase coverage, 73% recommendations accepted.
- DX Core 4 2024 (N=38,880): self-reported ~3h45m/week saved.

**Convergent:**
- PR/diff size = master variable.
- AI raises throughput, degrades stability.
- Developer overconfidence is real and replicated.
- LLM reviewers help most on triage / unfamiliar code; least on critical/familiar.

**Conflicting:**
- Magnitude of productivity gain (lab inflates, field deflates).
- Whether AI tests are "good" — depends on filtering pipeline.
- AI-reviewer recall — vendor 82%, academic <90% threshold needed for replacement.

**Open questions (nobody answered):**
- Do reviewers rubber-stamp agent-authored PRs? No eye-tracking study.
- Defect-escape-to-prod rate per AI co-authored PR with matched controls + 90-day window.
- Review-comment-to-defect ratio for LLM reviewers in production.
- AI-assisted review → cognitive deskilling (analog to GPS / aviation).
- Optimal human-AI division of labor by PR type.

Sources: smartbear.co (Cisco) ; microsoft.com/.../ICSE2013-codereview.pdf ; storage.googleapis.com/.../4476.pdf (Sadowski) ; arxiv.org/abs/2211.03622 (Perry) ; arxiv.org/abs/2302.06590 (Peng) ; gitclear.com/ai_assistant_code_quality_2025_research ; dora.dev/research/2024/dora-report ; apiiro.com/blog/4x-velocity-10x-vulnerabilities ; snyk.io/reports/secure-adoption-in-the-genai-era ; arxiv.org/abs/2402.09171 (TestGen-LLM) ; getdx.com.

---

## Round 2 — PR types deep-dive

### 6. PR / change-type taxonomies

**Canonical 14-type spine** drawn from Conventional Commits, Angular, gitmoji, Kubernetes `kind/*`, Linux kernel patches, Swanson maintenance taxonomy:

feat, fix, perf, refactor, docs, test, build, ci, chore, style, revert, deps, security, api-change.

**Orthogonal axes (8) compose multiplicatively:**
1. scope/area (Angular 23 scopes; k8s `area/*`/`sig/*`; Rust `A-*`/`T-*`).
2. size — XS (0-9), S (10-29), M (30-99), L (100-499), XL (500-999), XXL (1000+); Graphite 1.5M PR analysis: 200-400 line PRs have 40% fewer defects than larger.
3. risk tier / priority (k8s 5-tier `priority/*`).
4. blast radius — independent of size.
5. reversibility — Bezos one-way / two-way doors.
6. generated vs handwritten — k8s size labels exclude generated files.
7. author class — human / AI-assisted / bot. CLAVE stylometry 2025 shows distinct review needs.
8. SemVer impact — major / minor / patch / none.

**CC gaps (common in real codebases, missing from CC):**
- `deps` (Dependabot/Renovate dominant, no first-class type).
- `security` (highest risk class, no type).
- `schema/migration` — expand-migrate-contract pattern needed.
- `flag-flip` — one-line PR, huge blast radius.
- `config-only / IaC` — Terraform/Helm/k8s.
- `generated-code-only` — protobuf, OpenAPI, lockfile, snapshot.
- `api-change` — k8s `kind/api-change` precedent; CC handles only via `!` marker.
- `eval / prompt` — versioned artifacts with eval gates.
- `experiment / A-B`.
- `i18n / a11y`.
- `data-fix` — one-off SQL, backfill.

**Recommendation: 10-type spine — user picks one.**
feat, fix, refactor, perf, docs, test, chore (folds build/ci/style), deps, security, migration, config — plus prompt/skill if AI-orchestration relevant. Reason to elevate `migration`/`security`/`deps`/`config` out of CC: each radically changes the review checklist.

Sources: conventionalcommits.org/v1.0.0 ; karma-runner.github.io/6.4/dev/git-commit-msg.html ; gitmoji.dev ; github.com/kubernetes/test-infra/blob/master/label_sync/labels.md ; docs.kernel.org/process/submitting-patches.html ; semver.org ; arxiv.org/html/2506.17323v1 (CLAVE) ; graphite.com/guides/best-practices-managing-pr-size.

---

### 7. Per-type review concerns

| Type | Top reviewer concerns | AI failure mode |
|------|----------------------|-----------------|
| feat | API shape, breaking surface, telemetry, flag wrap, eval coverage, doc co-change | Auth header changed in 1 service, downstream silent fail (Apiiro). +153% architectural flaws |
| fix | Failing test now passing, root-cause vs symptom, blast radius, "Fixes:" trailer | Symptomatic patches → unmerged disproportionately |
| refactor | Behavior preserved, test diff = empty/renames only, rollback safety. Highest comment density | "Refactor" = re-paste. Code-clone 4x. Refactor share 25%→<10% |
| perf | Before/after numbers, regression test pinned, hot-path validation | 8x more excessive-I/O. Confident speedup w/o benchmarks |
| chore/build/ci | Reproducibility, lockfile, secret leak, supply-chain | Cloud creds leaked 2x more in CI files. Highest rubber-stamp (74-92% accept) |
| docs | Compilation, link-rot, API drift | Hallucinated examples, version drift |
| test | Assertion strength (mutation kill), flake (Assertion Roulette + Sleepy Test), **removed assertions** | Delete failing tests / weaken assertions to green CI |
| deps/security | CVE link, provenance (Sigstore/SLSA), **slopsquatting**, license, SBOM | 20% packages don't exist. 43% recur deterministically. 205k catalogued names |
| migration/schema | Expand-migrate-contract, lock-time, rollback DDL, nullable+default | DROP COLUMN no phasing. No double-run idempotency check |
| config/flag | One flag per behavior, ramp+kill-switch, expiry+owner+cleanup ticket | Stale flag explosion, no cleanup link |
| prompt/skill | Eval delta on golden set, adversarial set incl injection, tool-call scope, sandbox/egress | Pass happy-path, open injection surface |

**Self vs peer split per type:**
- feat: self = happy path; peer = API + downstream blast.
- fix: self = symptom; peer forces root cause + regression test.
- refactor: self **worst** here (confirmation bias). Peer + bisect catches.
- perf: self skips numbers; peer must demand.
- chore/CI: both rubber-stamp → automate (lockfile, secret-scan, OWASP).
- test: self weakens assertions; peer must read **removed** lines.
- deps: self trusts import; peer verifies package exists + CVE applies.
- migration: self validates dev; peer checks lock + online + rollback.

**Three types where AI most increased burden:** refactor (clone rate 4x), feat (1.7x issues/PR, 90th = 26 issues), deps/security (slopsquatting new failure class).

**Two types AI reviewers underserve today:** test changes (no tool flags assertion weakening / removed cases), schema/migration (no migration-class taxonomy, no rollback DDL requirement, no double-run check).

Sources: coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report ; apiiro.com/blog/4x-velocity-10x-vulnerabilities ; gitclear.com/ai_assistant_code_quality_2025_research ; arxiv.org/html/2509.14745v3 (agentic acceptance rates) ; arxiv.org/html/2602.00164 (fix-PRs unmerged) ; arxiv.org/html/2505.08005v1 (refactor bug-proneness) ; snyk.io/articles/slopsquatting-mitigation-strategies ; planetscale.com/blog/safely-making-database-schema-changes ; docs.launchdarkly.com/guides/flags/technical-debt ; promptfoo.dev/docs/guides/evaluate-coding-agents.

---

### 8. Self-review vs peer-review

**Cognitive model:**
- Self-review: catches **intent**, fails at **what's on page** (familiarity blindness; self-generation effect makes mistake detection harder, not easier — Springer 2022).
- Peer review: catches **what's on page**, misses **intent** (no recall). Pair programming +15% defect reduction; Fagan inspections 60-65% defect detection.

**Big shift:** AI-assisted author has *neither* familiarity blindness nor intent-recall advantage. Role inverted toward peer reviewer.

**Self-review focus (AI author):**
- Intent fidelity (matches prompt/spec?).
- Scope adherence (>5 unrelated files = flag — GitHub).
- Integration w/ surrounding code (duplicates, ignored helpers — Thoughtbot's #1 AI failure).
- Prompt/skill/rule coupling.
- Test/eval co-change.
- PR Contract (Osmani): intent / proof / risk / AI sections / focus areas.

**Peer review focus:**
- Architectural fit.
- Blast radius / cross-service.
- Regression risk.
- Knowledge transfer / ownership (comprehension debt — Anthropic RCT: AI-assisted engineers scored 17% lower on follow-up comprehension).
- Security on auth/payments (GitHub 8-9 min slot).

**Failure modes per persona:**
- Self-review: plausibility rubber-stamp, lost intent reconstruction, invisible scope creep, same-model blindspots.
- Peer-review: throughput collapse (Faros: high-AI-adoption +91% review time), architectural context absent, confident-fluent prose lulls, intent invisibility.

**UX implications:** different surfaces, shared diff primitive.
- Self-review (pre-PR): foreground intent capture, prompt/skill diff sidebar, scope-creep flag, "explain in own words" → becomes PR description (forces self-explanation, Chi et al. effect). Staging review, not commit dialog.
- Peer (PR): foreground architectural context, call graph, blast-radius map, downstream consumers. Author's Contract pinned at top. Risk-tier badge drives default depth.
- Cross-cutting: different AI on second pass (BugBot insight). Adversarial subagent at author stage (Cherny rubric-as-loss-function).

**3 most actionable patterns from 2025-2026:**
1. PR Contract enforced — refuse to open if blank.
2. Adversarial subagent before peer review (BugBot resolution 52% → 80% w/ learned rules).
3. Move human checkpoint upstream — review spec, not diff.

Sources: link.springer.com/article/10.1007/s00426-022-01699-3 ; thoughtbot.com/blog/how-to-review-ai-generated-prs ; addyo.substack.com/p/code-review-in-the-age-of-ai ; addyosmani.com/blog/comprehension-debt ; lucumr.pocoo.org/2025/9/29/90-percent ; mitchellh.com/writing/my-ai-adoption-journey ; cursor.com/blog/bugbot-learning ; howborisusesclaudecode.com ; intercom.com/blog/ai-is-approving-our-pull-requests-heres-how-we-made-it-safe ; latent.space/p/reviews-dead.

---

### 9. Type-aware tooling landscape

**Stack mature except UI.** Layers exist:
1. Classification — actions/labeler, TimonVS/pr-labeler-action, srvaroa/labeler, Renovate semantic-commits, Dependabot security PRs.
2. Routing — buildsville/assign-reviewer-by-label, Aviator MergeQueue per-label policies, Ona auto-approval (74% lead-time cut).
3. CI / checks — Buildkite git-diff-conditional, Atlas migration linting, CodSpeed (perf-only), Snyk PR Checks, Conftest/OPA (config), Braintrust (prompts).
4. AI reviewer specialization — Cloudflare 7-agent risk-tiered ($0.98/review, 3m39s median, 85.7% cache hit), CodeRabbit path-based instructions, Cursor BugBot + BUGBOT.md (resolution 52% → ~80% w/ learned rules), Graphite Agent.

**UI layer is laggard.** GitHub Files Changed renders identically for 3-line typo fix, 12-file schema migration, prompt change. No mainstream review tool re-orders panels, hides irrelevant signals, or surfaces type-specific checklists *inline* in the diff.

**Specific gaps nobody fills well:**
1. Review UI doesn't adapt to type.
2. Mixed-type "monster PRs" — no tool splits review surface so migration part is reviewed against migration rules and UI part against UI rules.
3. Type-axis hardcoded per tool — no standard "PR-type manifest" exists.
4. Gaming the label trivial — only Ona addresses with platform-owned classifier.
5. Type-conditional checklists live in markdown, not bound to diff hunks.
6. No standard for type-aware test impact analysis at review surface.
7. Per-type AI reviewer prompts siloed — no portable "reviewer manifest" across tools.

**MVP recommendation:**
1. 6-8 type taxonomy keyed off path globs + CC prefix + LLM tiebreaker. Suggested: feat, fix, refactor, migration, deps, docs, config, prompt/eval. Cloudflare-style risk tier (trivial / standard / sensitive) as orthogonal axis.
2. **Type-conditional review checklist rendered inline in diff** — for `migration`, show rollback / lock / data-loss prompts on SQL hunks. For `deps`, show CVE / license / install-script signals on lockfile hunks. **The missing UI primitive everyone else skipped — biggest single wedge.**
3. One AI reviewer agent per type with tightly-scoped system prompt + explicit "what to ignore" list (Cloudflare's key insight).
4. **Type manifest file (`.review/types.yaml`)** binds type → globs → checklist → required reviewers → required checks → AI agent prompt. Missing portability layer; auditable; prevents label-gaming because manifest is platform-owned.

Skip in MVP: full risk-tiered model routing, auto-approval, virtual-branch PR splitting.

Sources: github.com/actions/labeler ; docs.renovatebot.com/semantic-commits ; docs.aviator.co/mergequeue/configuration-file ; ona.com/stories/auto-approving-low-risk-prs ; atlasgo.io ; codspeed.io ; docs.snyk.io/scan-with-snyk/pull-requests/pull-request-checks ; conftest.dev ; blog.cloudflare.com/ai-code-review ; docs.coderabbit.ai/guides/review-instructions ; cursor.com/docs/bugbot ; cursor.com/blog/bugbot-learning ; graphite.dev/docs/diamond ; braintrust.dev/articles/best-ai-evals-tools-cicd-2025.
