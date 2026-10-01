"""Run from the repo root: python3 tests/check-ci.py (requires PyYAML)."""
import os
from pathlib import Path
import subprocess
import tempfile
import yaml


def run(cmd, **kwargs):
    return subprocess.run(cmd, text=True, capture_output=True, **kwargs)


check = yaml.safe_load(Path('.github/workflows/r-cmd-check.yaml').read_text())
job = check['jobs']['r-cmd-check']
assert 'TESTTHAT_PARALLEL' not in job['env']
step = next(s for s in job['steps'] if s['name'] == 'Disable parallel tests on Windows')
assert step['if'] == "startsWith(matrix.config.os, 'windows') && !inputs.testthat-parallel-windows"
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, GITHUB_ENV=f'{tmp}/env')
    assert run(['bash', '-eu', '-c', step['run']], env=env).returncode == 0
    assert Path(env['GITHUB_ENV']).read_text() == 'TESTTHAT_PARALLEL=FALSE\n'

lint = yaml.safe_load(Path('.github/workflows/commit-lint.yaml').read_text())
script = lint['jobs']['commit-lint']['steps'][-1]['run']
with tempfile.TemporaryDirectory() as tmp:
    def git(*args):
        result = run(['git', *args], cwd=tmp)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    git('init', '-q')
    git('config', 'user.email', 'test@example.org')
    git('config', 'user.name', 'Test Author')
    git('commit', '--allow-empty', '-qm', 'ci: initial')
    base = git('rev-parse', 'HEAD')
    for author, subject, expected in [
        ('Test Author', 'feat(API): valid uppercase scope', 0),
        ('Test Author', 'fix(phase36_1): valid scope', 0),
        ('Test Author', 'fix(bad-scope): invalid scope', 1),
        ('github-actions[bot]', 'bad subject', 1),
        ('dependabot[bot]', 'bad subject', 1),
        ('github-actions[bot]', 'ci: valid bot subject', 0),
    ]:
        git('config', 'user.name', author)
        git('commit', '--allow-empty', '-qm', subject)
        head = git('rev-parse', 'HEAD')
        env = dict(os.environ, TYPES='feat|fix|refactor|perf|build|test|ci|docs|style|chore',
                   SCOPE_REGEX='[A-Za-z0-9_]+', BASE_SHA=base, HEAD_SHA=head,
                   PR_TITLE='ci: test validation', PR_AUTHOR='test-user', GITHUB_HEAD_REF='fix/test-ci')
        result = run(['bash', '-eu', '-o', 'pipefail', '-c', script], cwd=tmp, env=env)
        assert result.returncode == expected, (author, subject, result.stdout, result.stderr)
        base = head
print('CI regression checks passed')
