# Changelog

## [Unreleased]

### Breaking Changes
- Removed legacy glitchling parameter aliases (e.g., `max_change_rate`, `replacement_rate`) in favour of the standard `rate` keyword across the zoo. Update custom integrations to pass `rate` only.
- Dropped support for the deprecated YAML `type:` key in attack configurations; declarative rosters must now specify `name:` for each glitchling.
- Inlined default `rate` handling within each glitchling and removed the `glitchlings.zoo._rate` helper module.

