#!/usr/bin/env python3
"""Check tracked portfolio files for private material; never print matching values."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {'.env', 'id_rsa', 'id_ed25519'}
FORBIDDEN_SUFFIXES = {'.sqlite', '.db', '.pem', '.key', '.p12', '.pfx'}
FORBIDDEN_DIRS = {'.catalog-cache', 'replay', 'node_modules', '__pycache__'}
EMAIL = re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', re.I)
SECRETS = re.compile(
    r'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|'
    r'sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|'
    r'AIza[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
)


def main():
    issues = []
    tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT,
                             capture_output=True, check=False)
    paths = ([ROOT / name.decode() for name in tracked.stdout.split(b'\0') if name]
             if tracked.returncode == 0 else ROOT.rglob('*'))
    for path in paths:
        if not path.is_file() or '.git' in path.relative_to(ROOT).parts:
            continue
        relative = path.relative_to(ROOT)
        if (path.name in FORBIDDEN_NAMES or path.name.startswith('.env.')
                or path.suffix in FORBIDDEN_SUFFIXES
                or FORBIDDEN_DIRS.intersection(relative.parts)):
            issues.append(f'{relative}: private file')
            continue
        if relative.parts[0] == 'assets' and path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            issues.append(f'{relative}: unexpected binary file')
            continue
        if SECRETS.search(content):
            issues.append(f'{relative}: possible credential')
        if any(not match.group().endswith('@users.noreply.github.com')
               for match in EMAIL.finditer(content)):
            issues.append(f'{relative}: email address')
    for issue in issues:
        print(issue)
    print('Public snapshot ready' if not issues else f'{len(issues)} issue(s) found')
    return bool(issues)


if __name__ == '__main__':
    raise SystemExit(main())
