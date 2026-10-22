"""Coverage comparison with frozen v1; same document geometric perturbations only."""
from collections import Counter
from pathlib import Path
import json,sys
from benchmark import VARIANTS,make_variant,make_two_page
from parser_v2 import run as v2_run
sys.path.insert(0,str(Path(__file__).parent/'tests'))
from baseline_parser import run as v1_run

ROOT=Path(__file__).resolve().parent
cases={'original':ROOT/'source.pdf','scaled_79':VARIANTS/'scaled_79.pdf',
    'scaled_123':VARIANTS/'scaled_123.pdf','translated':VARIANTS/'translated.pdf',
    'distractor_footer':VARIANTS/'distractor_footer.pdf', 'two_pages':VARIANTS/'two_pages.pdf'}
results=[]
for label,p in cases.items():
    a=v1_run(p);b=v2_run(p)
    result={'variant':label,'v1_monetary_rows':a['stats']['monetary_rows'],
        'v2_monetary_rows':b['stats']['monetary_rows'],
        'v1_issues':len(a['issues']),'v2_issues':len(b['issues']),
        'v1_periods':[x.get('period_previous') for x in a['page_metadata']],
        'v2_periods':[x['periods'] for x in b['pages']]}
    results.append(result)
    print(label,'v1',result['v1_monetary_rows'],'v2',result['v2_monetary_rows'])
(ROOT/'output'/'baseline_comparison.json').write_text(json.dumps({'methodology':'v1 frozen baseline vs v2 on the same transformed page; no out-of-distribution accuracy claim','results':results},ensure_ascii=False,indent=2))
