fix(ui): make existing providers and datasets read-only

Why:
- Prevent accidental editing of saved provider and dataset configurations.

What changed:
- Disabled all form controls when an existing record is selected.
- Hid save actions and removed update submission paths.

Validation:
- npm run lint; npm run build

Notes:
- Lint passes with three pre-existing warnings.
