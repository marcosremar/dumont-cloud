# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-01-01 06:02]
Some components incorrectly reference 'dark-surface-bg' which doesn't exist in tailwind config. The correct reference for the page background is 'dark-surface' (without -bg suffix) which maps to the DEFAULT value #0a0d0a.

_Context: Slider and Switch components were using dark:focus-visible:ring-offset-dark-surface-bg which is invalid. Use dark:focus-visible:ring-offset-dark-surface instead._
