<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the DHG Patchbay docs site. The existing `posthog-docusaurus` plugin was already wired for automatic pageview tracking; this run layered in explicit `posthog.capture()` calls for every meaningful user interaction on the Patchbay landing page. The `docusaurus.config.ts` was updated to load the PostHog API key and host from environment variables (via `dotenv`) instead of hardcoded values. Ten event types now cover the full Patchbay interaction surface — from Talkback AI questions to service module clicks, jack link navigation, documentation tape access, and offsite link follows.

| Event | Description | File |
|-------|-------------|------|
| `talkback_question_asked` | User submits a question to the Talkback AI assistant on the Patchbay. | `src/components/Patchbay/index.tsx` |
| `talkback_error` | An error occurred while the Talkback AI assistant was processing a response. | `src/components/Patchbay/index.tsx` |
| `talkback_closed` | The Talkback monitor panel was closed by the user. | `src/components/Patchbay/index.tsx` |
| `suggestion_chip_clicked` | User clicked one of the pre-defined suggestion chips in the Talkback panel. | `src/components/Patchbay/index.tsx` |
| `module_clicked` | User clicked on a service module tile to open the associated service URL. | `src/components/Patchbay/index.tsx` |
| `jack_clicked` | User clicked a specific jack (TUNNEL, LAN, or TS) link on a service module. | `src/components/Patchbay/index.tsx` |
| `documentation_tape_clicked` | User clicked on a documentation tape to navigate to a project docs section. | `src/components/Patchbay/index.tsx` |
| `offsite_link_clicked` | User clicked an external offsite link from the Patchbay footer links section. | `src/components/Patchbay/index.tsx` |
| `service_filter_used` | User typed a search query in the Patchbay filter strip to find services (debounced 800 ms). | `src/components/Patchbay/index.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard**: [Analytics basics (wizard)](https://us.posthog.com/project/255160/dashboard/1887865)
- [Talkback questions over time (wizard)](https://us.posthog.com/project/255160/insights/P2pvU20H) — daily AI question volume
- [Top clicked service modules (wizard)](https://us.posthog.com/project/255160/insights/kFW4Rw5c) — which services get the most opens
- [Talkback errors vs questions (wizard)](https://us.posthog.com/project/255160/insights/vPGYNLcn) — reliability ratio to watch
- [Patchbay engagement funnel (wizard)](https://us.posthog.com/project/255160/insights/Qrt1lB2t) — Talkback → docs conversion
- [Jack type usage breakdown (wizard)](https://us.posthog.com/project/255160/insights/bHxaQODq) — TUNNEL vs LAN vs TS preference

## Verify before merging

- [ ] Run a full production build (the wizard only verified the files it touched) and fix any lint or type errors introduced by the generated code.
- [ ] Run the test suite — call sites that were rewritten or instrumented may need updated mocks or fixtures.
- [ ] Run `npm install` to install the `dotenv` devDependency added to `package.json`, then verify `npm run build` succeeds with environment variables loaded from `.env`.
- [ ] Add `POSTHOG_API_KEY` and `POSTHOG_HOST` to `.env.example` and any CI/CD bootstrap scripts so collaborators know what to set.
- [ ] Wire source-map upload (`posthog-cli sourcemap` or your bundler's upload step) into CI so production stack traces de-minify.

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-javascript_node/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
