# /latest — show the most recent analyst report

Finds and displays the latest recommendations JSON.

```bash
ls -t data/research/recommendations/*.json 2>/dev/null | head -1 | xargs python3 -c "import sys,json; d=json.load(open(sys.argv[1])); [print(f'{r[\"ticker\"]:6} {r[\"action\"]:4} {r[\"confidence\"]:6} {r[\"allocation_pct\"]:5.1f}%  {r[\"rationale\"][0][:60]}') for r in d['recommendations']]"
```

Shows: ticker, action, confidence, allocation %, first rationale bullet.
