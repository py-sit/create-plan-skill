# PDF quality contract

A render is acceptable only when:

- the document uses the requested language consistently;
- cover, headings, tables, lists, code, links, and diagrams are legible;
- no page is blank, clipped, unexpectedly rotated, or missing glyphs;
- tables do not overflow the printable page;
- local source paths are visible only as relative labels and never as
  `file://` links;
- external HTTPS links remain clickable;
- the reviewed and delivered PDF hashes match;
- every page has been rendered to an image and inspected.

Playwright/Chromium is the primary V2 renderer. ReportLab is an explicit
compatibility fallback, not an invisible substitute.
