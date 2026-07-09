---
name: frontend-engineer
description: Conventions for the browser UI in ui/. Use when editing React components, hooks, routing, forms, or Tailwind styling.
---

# Frontend engineer

Stack: React 19 + TypeScript, Vite, Tailwind v4, react-router-dom 7, react-hook-form. Match `ui/src`.

- Function components + hooks only. No class components.
- TypeScript strict — type props and API responses; no `any`. Share request/response types with the backend contract.
- Forms use react-hook-form (`useForm`, `register`, `handleSubmit`); don't hand-roll controlled-input state.
- Styling is Tailwind utility classes in JSX. No CSS-in-JS, minimal separate stylesheets.
- Routing via react-router-dom 7 (data routers / `<Routes>` as already used); keep route definitions centralized.
- Keep fetch logic in hooks/services, not inline in components. Handle loading and error states explicitly.
- Small, focused components; lift state only as far as needed.

## Checks before done
- `npm run lint` clean.
- `npm run build` (tsc + vite) passes with no type errors.
- No horizontal overflow; layout holds on narrow widths.
