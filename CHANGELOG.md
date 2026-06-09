# Changelog

All notable changes to this project will be documented in this file.

## [1.0.2] - 2026-06-09

- Updated homepage, about, resume, work, paginated work, and sample case study metadata to describe the project as an Astro theme for UI/UX designer portfolios.
- Improved shared SEO defaults with richer structured data, support for page-specific Open Graph types, and customizable Open Graph image alt text.
- Added page-specific structured data and `article` Open Graph metadata for the sample Nextpoint case study.
- Made canonical URLs, `robots.txt`, and sitemap generation honor `SITE_URL` or `PUBLIC_SITE_URL` so deployments do not point back to the demo domain.
- Excluded `noindex` legal pages from the generated sitemap.
- Documented the new environment-based SEO URL setup in the README.

## [1.0.1] - 2026-06-06

- Added a project changelog for release tracking.
- Added `AGENTS.md` with repo-specific guidance for future contributors and coding agents.
- Fixed the brief font flash on page load by preloading the self-hosted Manrope font and using a custom `@font-face` declaration with a less jarring display strategy.

## [1.0.0] - 2026-06-04

- Initial release of the Maria Astro portfolio theme.
- Added the homepage, work listing, case study, about, resume, privacy, terms, cookies, and 404 pages.
- Added shared site configuration, SEO defaults, structured data, sitemap generation, and `robots.txt`.
- Added persistent light and dark mode, cookie consent UI, and responsive portfolio assets.
