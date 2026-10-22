# Viewer

Static page, no server and no dependencies. `python scripts/build_viewer.py --run native_grid=fin1 --run docling_cmtrue=fin1 ...` writes `data.js` and page images
(`pages/`, git-ignored: they are renders of third-party filings), then open `index.html`. Pick a page and backend; click a box on the page or a cell in the table to see
the exact printed string, typed value, status, evidence kind and notes; the *Review warnings* tab lists run status, issues and flagged cells (click to jump to the box); *Scores vs AI-draft*
shows the stored evaluator numbers and cell errors; *AI-draft reference* overlays the unverified reference boxes. Deep links: `index.html?doc=daiwabo_p10&backend=native_v2&tab=warn&cell=0.1.0&ref=1`.
It displays stored predictions only; it cannot run a backend and does not edit anything.
