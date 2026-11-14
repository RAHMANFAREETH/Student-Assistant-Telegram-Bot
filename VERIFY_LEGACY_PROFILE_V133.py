"""Offline independent-corpus verification for imported Tamil/Sinhala profiles.

Reference pairs must come from an independent reviewed source, not be copied
blindly from a profile's own samples. No text or paths sent to a server.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from AUDIT_CONVERT_LEGACY_DOCX_V133 import decode,validate_profile

def verify(profile,records):
    checked=validate_profile(profile)
    if not isinstance(records,list) or len(records)<5 or len(records)>5000:
        raise ValueError('Provide 5–5,000 independently reviewed example pairs')
    failures=[]
    for idx,record in enumerate(records,1):
        if not isinstance(record,dict) or not isinstance(record.get('legacy'),str) or not isinstance(record.get('unicode'),str):
            failures.append({'index':idx,'error':'malformed reference example'});continue
        try:
            actual=decode(record['legacy'],checked)
            if actual!=record['unicode']:failures.append({'index':idx,'error':'Unicode mismatch'})
        except ValueError as e:failures.append({'index':idx,'error':str(e)})
    return {'profile':checked['font'],'language':checked['language'],'reference_cases':len(records),'passed':len(records)-len(failures),'failed':len(failures),'failures':failures[:30], 'note':'Checks compare to supplied independent references; no guarantee for untested documents.'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('profile',type=Path);p.add_argument('independent_reference_json',type=Path)
    args=p.parse_args()
    raw=json.loads(args.profile.read_text(encoding='utf-8'))
    refs=json.loads(args.independent_reference_json.read_text(encoding='utf-8'))
    result=verify(raw,refs)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['failed']:raise SystemExit(1)
if __name__=='__main__':main()
