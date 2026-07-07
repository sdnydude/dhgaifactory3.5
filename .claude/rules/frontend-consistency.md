# Frontend Consistency — reuse before create (Next.js rebuild)

Applies to the `frontend/` Next.js app.

## Before creating anything
- **Search first.** Before writing a new component, hook, or utility, search `frontend/src/components/`, `frontend/src/hooks/`, and `frontend/src/lib/` for an existing equivalent. Extend or compose what exists rather than adding a parallel implementation.
- **Extend shadcn/ui primitives.** Build on the existing shadcn/ui components; do not hand-roll a second Button/Dialog/Input alongside them.
- **A new shared component needs a one-line justification** in its PR/commit of why nothing existing fit. If you can't state it, reuse instead.

## Styling
- **Colors come from the dhg-brand CSS tokens** — no raw hex in components. Use the token variables; see `dhg-brand.md` for the palette (do not duplicate the values here).

## State
- **One store pattern.** Shared state lives in `frontend/src/stores/`. No ad-hoc state containers, context-as-store hacks, or parallel global-state mechanisms.

## Utilities
- Shared helpers belong in `frontend/src/lib/`; don't inline a copy of logic that already lives there.
