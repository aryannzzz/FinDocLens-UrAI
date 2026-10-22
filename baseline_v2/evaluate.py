"""Evaluation on manually transcribed independent reference TSV (provided PDF only)."""
import argparse,csv,json
from pathlib import Path
from parser_v2 import run

def read_gold(path):
    with open(path,encoding='utf-8') as f:return list(csv.DictReader(f,delimiter='\t'))

def measure(pred,gold):
    n=len(gold);m=len(pred);paired=min(n,m)
    row_labels=sum('/'.join(pred[i]['path'])==gold[i]['path'].split('/')[-1] for i in range(paired))
    correct_labels=sum(pred[i]['label']==gold[i]['path'].split('/')[-1] for i in range(paired))
    correct_paths=sum('/'.join(pred[i]['path'])==gold[i]['path'] for i in range(paired))
    correct_types=sum(pred[i]['type']==gold[i]['type'] for i in range(paired))
    cell_total=0;exact=0;sem=0;matched=0
    from parser_v2 import normalize_amount
    for i in range(paired):
        if gold[i]['type']=='section':continue
        if pred[i]['type']=='section':continue
        for j,key in enumerate(('raw_2025','raw_2026')):
            cell_total+=1
            if len(pred[i]['cells'])>j:
                matched+=1
                raw=pred[i]['cells'][j]['raw']; gold_raw=gold[i][key]
                exact+=int(raw==gold_raw)
                sem+=int(raw is not None and normalize_amount(raw)==normalize_amount(gold_raw))
    return {'gold_rows':n,'pred_rows':m,'sequence_complete':n==m,'label_exact':correct_labels,'path_exact':correct_paths,'row_type_exact':correct_types,'gold_monetary_cells':sum(x['type']!='section' for x in gold)*2,'matched_cells':matched,'evaluated_cells':cell_total,'raw_cell_exact':exact,'semantic_cell_exact':sem,
      'label_accuracy':round(correct_labels/n,4),'path_accuracy':round(correct_paths/n,4),'raw_cell_accuracy':round(exact/(sum(x['type']!='section' for x in gold)*2),4)}

def main():
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('--gold',default='tests/gold_rows.tsv');p.add_argument('--out',default='output/evaluation.json');a=p.parse_args()
    pred=run(a.pdf)['rows']; gold=read_gold(a.gold); metrics=measure(pred,gold)
    Path(a.out).parent.mkdir(exist_ok=True,parents=True)
    Path(a.out).write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
