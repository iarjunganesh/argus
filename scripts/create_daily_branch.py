#!/usr/bin/env python3
import subprocess,sys,os
from collections import OrderedDict

BACKUP_BRANCH = 'backup/main-before-rewrite-2026-06-08'
DAILY_BRANCH = 'cleaned/main-daily-2026-06-08'

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

# Get commits in reverse (oldest -> newest)
commits = run(f'git rev-list --reverse {BACKUP_BRANCH}').splitlines()
if not commits:
    print('No commits found on backup branch', file=sys.stderr); sys.exit(1)

# Map date -> last commit of that date
date_map = OrderedDict()
for c in commits:
    ai = run(f'git show -s --format=%ai {c}')
    date = ai.split()[0]  # YYYY-MM-DD
    date_map[date] = c

print(f'Found {len(commits)} commits across {len(date_map)} dates')

# Create orphan branch
run(f'git checkout --orphan {DAILY_BRANCH}')
# remove all files from index and worktree
run('git rm -rf . || true')
# ensure clean
open('.gitignore','a').close()

first = True
for date, c in date_map.items():
    print('Processing', date, c)
    # checkout tree of commit into worktree
    run(f'git checkout {c} -- .')
    # add all
    run('git add -A')
    author_date = date + ' 12:00:00'
    env = os.environ.copy()
    env['GIT_AUTHOR_DATE'] = author_date
    env['GIT_COMMITTER_DATE'] = author_date
    msg = f"Snapshot {date} ({c})"
    # commit
    # Use subprocess.run to set env
    res = subprocess.run(['git','commit','-m',msg], env=env)
    if res.returncode != 0:
        print('No changes to commit for', date)

print('Daily branch created:', DAILY_BRANCH)
print('Pushing branch to origin...')
run(f'git push origin {DAILY_BRANCH}')
print('Done.')
