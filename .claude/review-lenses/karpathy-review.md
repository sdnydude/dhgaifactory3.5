# Karpathy Review Lens

A review-time lens, NOT an always-loaded rule. Cite this from /ship Phase 6
(review agents) or apply it in a main-session self-review. It turns Andrej
Karpathy's four coding guidelines into concrete reviewer checks. The full
guidelines already live in global CLAUDE.md; this is the *enforcement* slice —
what a reviewer should actually flag.

Apply per changed file. For each finding, name the file:line and the guideline
it violates. A change that is clean on all four passes the lens.

## 1. Think before coding — were assumptions surfaced?
- Flag code that silently commits to one interpretation of an ambiguous spec
  where another reading was plausible and unaddressed.
- Flag a complex path taken where a simpler one was available and unmentioned.
- Not greppable — judgment call. Ask: "would a reviewer be surprised by an
  unstated assumption baked into this change?"

## 2. Simplicity first — is this the minimum that solves the problem?
- Flag speculative generality: config/flags/abstraction for a single call site,
  "flexibility" nobody asked for, error handling for impossible states.
- Flag a 200-line implementation of a 50-line problem.
- Signal: a new class/interface/param with exactly one caller and no second one
  in sight. Grep aid: `grep -rn "def .*(" <changed>` then check call sites.

## 3. Surgical changes — did the diff touch only what was asked?
- Flag reformatting, renaming, or "while we're here" edits to lines unrelated to
  the task; flag deletion of pre-existing (not newly-orphaned) dead code.
- Newly-unused imports/vars introduced BY this change must be removed; pre-existing
  ones are out of scope.
- Grep aid: skim `git diff --stat` — files touched that the task never named are
  the first suspects.

## 4. Goal-driven execution — is success actually verified?
- Flag "should work" claims with no test, no run, no observed output.
- A bugfix without a test that reproduces the bug; a feature without a test that
  exercises it; a refactor with no before/after green run.
- Grep aid: `grep -rn "TODO\|FIXME\|XXX\|placeholder\|pass  #\|raise NotImplementedError" <changed>`
  and confirm every new behavior has a corresponding test file change.

## Verdict
- **Critical (blocks the Phase 6 gate):** unverified behavior shipped as done;
  a non-surgical change that alters unrelated production paths.
- **Important:** speculative complexity; unstated load-bearing assumption.
- **Minor:** cosmetic scope creep, redundant abstraction with low blast radius.
