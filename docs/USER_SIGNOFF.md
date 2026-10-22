# Human ground-truth sign-off

I inspected the rendered original Japanese financial statement (not merely a model-generated table), and verified the following independent cells and their parent/account context:

Original Ur AI supplied page: [ ] All labels/periods/units   [ ] all 74 monetary tokens
ELECOM page 9: [ ] selected table bbox   [ ] 20+ cell tokens + rows + headers
OMRON page 13: [ ] table count/group headers  [ ] 20+ amount/percentage/change cells
Daiwabo page 10: [ ] 3 distinct regions  [ ] 20+ tokens across side-by-side tables

Report each incorrect draft gold as a correction with source crop. Do not silently modify gold after viewing model errors. If not fully inspected, label scope and sample size explicitly (e.g. `human_checked_cells=20/44`).
