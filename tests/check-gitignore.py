"""Run from the repo root: python3 tests/check-gitignore.py (stdlib only)."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path('templates/config')
template = (root / '.gitignore').read_text()
python = (root / '.gitignore.python').read_text()

tracked = [
    'README.md', 'NEWS.md', 'LICENSE.md', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md', 'SECURITY.md',
    'DESCRIPTION', 'NAMESPACE', 'R/f.R', 'data/raw.csv', 'docs/guide.md', 'docs/index.html',
    'docs/nested/page.md', 'lib/helpers.R', 'build/out.txt', 'site/index.html', 'po/R-pkg.pot',
    '.github/workflows/ci.yaml', '.specmill/manifest.json', '.gitignore', '.gitattributes',
    '.gitleaks.toml', '.gitleaksignore', '.Rbuildignore', '.Rprofile', '.Renviron.example', '.lintr',
    '.nojekyll', '.pre-commit-config.yaml',
]
ignored = [
    'AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'HANDOFF.md', 'notes.md', '.claude/settings.json',
    '.planning/x', '.beans/x', '.beans.yml', '.worktrees/x', '.cursorrules', '.directory',
    '.Renviron', '.env', '.Rhistory', '.RData', '.Rproj.user/x', '.httr-oauth', 'vignettes/a.html',
    'rsconnect/x', 'src/foo.o', 'pkg_0.1.tar.gz', 'foo.Rcheck/x',
]
python_ignored = [
    '__pycache__/x.pyc', 'build/out.txt', 'dist/x.whl', 'lib/helpers.py', 'site/index.html', '.venv/x',
]
python_tracked = ['docs/guide.md', 'R/f.R', 'src/lib/helpers.R', 'data/build/x', 'po/R-pkg.pot', '.github/ci.yaml']

# A developer's global or system excludes must not change the result.
env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')


def check(rules, paths):
    """Return the subset of paths that git ignores under the given .gitignore text."""
    with tempfile.TemporaryDirectory() as tmp:
        def git(*args):
            return subprocess.run(['git', *args], cwd=tmp, text=True, capture_output=True, env=env)

        assert git('init', '-q', '.').returncode == 0
        Path(tmp, '.gitignore').write_text(rules)
        for path in paths:
            target = Path(tmp, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        # check-ignore exits 0 when the path is ignored and 1 when it is not; anything else is an error.
        codes = {p: git('check-ignore', '-q', p).returncode for p in paths}
        assert set(codes.values()) <= {0, 1}, codes
        return {p for p, code in codes.items() if code == 0}


assert check(template, tracked) == set(), check(template, tracked)
assert check(template, ignored) == set(ignored), set(ignored) - check(template, ignored)

combined = template + python
assert check(combined, python_ignored) == set(python_ignored), set(python_ignored) - check(combined, python_ignored)
assert check(combined, python_tracked) == set(), check(combined, python_tracked)

# The templates must not name agents or tools.
for name, text in (('.gitignore', template), ('.gitignore.python', python)):
    hit = re.search(r'AGENTS|CLAUDE|GEMINI|CODEX|CURSOR|COPILOT|AIDER|WINDSURF', text, re.I)
    assert hit is None, f'{name} names {hit.group(0)}'

print('Gitignore template checks passed')
