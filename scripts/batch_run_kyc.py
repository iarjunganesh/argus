"""Batch-run KYC requests against local ARGUS API and save reports.

Usage: python scripts/batch_run_kyc.py --count 10 --out data/reports_batch.jsonl
"""
import requests
import time
import argparse
import json
from pathlib import Path

API = "http://127.0.0.1:8000"


def submit(entity_name):
    payload = {
        'entity_name': entity_name,
        'entity_type': 'corporate',
        'jurisdiction': 'SE',
        'registration_number': 'BATCH-'+entity_name[:6],
        'aliases': [],
        'include_transaction_analysis': True,
    }
    # Retry on transient connection errors
    for attempt in range(1, 6):
        try:
            r = requests.post(f"{API}/api/v1/kyc/assess", json=payload, timeout=10)
            r.raise_for_status()
            return r.json()['report_id']
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ submit attempt {attempt} failed: {e}")
            time.sleep(attempt)
    raise ConnectionError('Failed to submit after retries')


def poll(report_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{API}/api/v1/kyc/status/{report_id}", timeout=5)
            r.raise_for_status()
            status = r.json().get('status')
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ poll transient error: {e}")
            time.sleep(1)
            continue
        if status == 'completed':
            r2 = requests.get(f"{API}/api/v1/kyc/report/{report_id}")
            r2.raise_for_status()
            return r2.json()
        time.sleep(1)
    raise TimeoutError('Poll timed out')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--out', type=Path, default=Path('data/reports_batch.jsonl'))
    parser.add_argument('--poll-timeout', type=int, default=180, help='Timeout seconds to wait for each report')
    args = parser.parse_args()

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)

    errors_file = out.parent / 'reports_batch_errors.jsonl'
    for i in range(args.count):
        name = f"BatchCo-{i+1:03d}"
        print('Submitting', name)
        try:
            rid = submit(name)
            print('  report_id', rid)
        except Exception as e:
            print(f"  ❌ submit failed for {name}: {e}")
            with errors_file.open('a', encoding='utf-8') as eh:
                eh.write(json.dumps({'entity': name, 'error': str(e)}) + '\n')
            continue

        try:
            report = poll(rid, timeout=args.poll_timeout)
        except Exception as e:
            print(f"  ❌ poll failed for {rid}: {e}")
            with errors_file.open('a', encoding='utf-8') as eh:
                eh.write(json.dumps({'report_id': rid, 'entity': name, 'error': str(e)}) + '\n')
            continue

        with out.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + '\n')
        print('  saved')


if __name__ == '__main__':
    main()
