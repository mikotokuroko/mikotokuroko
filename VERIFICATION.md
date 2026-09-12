# Profile README verification

- Implemented the requested single-column order, default captions, 560px room banner, 420px artwork, and collapsed credits. Generated regions start empty; permanent activity links remain visible.
- Six standard-library test cases pass: successful data, missing/unsafe artwork, empty/malformed/missing sources with independent updates, Unicode and Markdown/HTML punctuation, missing/duplicated/overlapping markers with no writes, editable captions/links, preservation outside markers, and idempotence (including unchanged modification time).
- Run the tests with `python3 -m unittest discover -s scripts -v`.
- Evaluated both templates with fixture plugin data: XML-escaped JSON retains long Unicode titles; empty feeds emit `null`; Steam keeps the existing preferred-game selection.
- Previewed GFM output using the already-installed Marked renderer and headless Chrome with GitHub-like typography and responsive image rules at 1100px and 320px, in light and dark themes. No horizontal overflow; both images loaded. Desktop image widths were 560px and 420px; both shrank to 272px within the mobile content area. Text remains understandable with images hidden. This is a local approximation of GitHub rendering.
- All referenced local assets exist. The preserved [Apple Music Local](https://github.com/mikotokuroko/apple-music-local-plugin), [Ark Codex Deskpet](https://github.com/mikotokuroko/Ark-codex-skill), and [Safari Dark Mode](https://github.com/mikotokuroko/safari-dark-mode) URLs resolve. The link checker could not load Apple Music or Steam; their permanent destinations match the configured playlist and account `76561199045338784`.
- The workflow retains Sunday 18:00 UTC and manual triggers. Each Metrics step can fail independently. The updater receives only successful outputs, reads them from `/metrics_renders`, and preserves invalid/empty sources. Metrics commits and SVG optimization are disabled; only changed README content is staged and pushed by the workflow. These output-path and output-action settings were checked against the [Metrics action source](https://github.com/lowlighter/metrics/blob/master/source/app/action/index.mjs).
- `git diff --check` passes. Live GitHub Actions fetching has not been run; the implementation is local and unpublished.

## Internal metadata interface

Each template emits one SVG `<metadata id="profile-data">` element containing XML-escaped JSON. Music uses `{"title": "…", "artist": "…", "artwork": "https://…"}`; Steam uses `{"title": "…", "icon": "https://…"}`. Empty feeds emit `null`. Missing or non-HTTP(S) artwork is omitted from the README.

Headings, explanations, project links, and captions are edited directly in `README.md`. Keep the exact MUSIC/STEAM markers. Keep each permanent activity link as the first paragraph after its END marker; the updater reads the link destination there, independently of its editable label. When changing the playlist or Steam account, update that link and the workflow input together.
