# /report — show the latest QA report

Displays the most recent QA report summary.

```bash
ls -t data/qa/*.json 2>/dev/null | head -1 | xargs python3 -c "
import sys, json
d = json.load(open(sys.argv[1]))
status = '✓ PASS' if d['success'] else '✗ FAIL'
print(f'{status}  {d[\"report_date\"]}')
print(f'Passed: {d[\"passed\"]}  Failed: {d[\"failed\"]}  Errors: {d[\"errors\"]}  Total: {d[\"total\"]}')
if not d['success']:
    print()
    print(d.get('output_tail', '')[-1000:])
"
```
