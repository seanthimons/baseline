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

release = yaml.safe_load(Path('.github/workflows/release-r-package.yaml').read_text())
steps = {s['name']: s for s in release['jobs']['check']['steps']}
assert steps['Checkout repository']['with']['persist-credentials'] is False
assert 'token' not in steps['Checkout repository']['with']
secret_steps = [name for name, step in steps.items() if 'secrets.RELEASE_PAT' in str(step)]
assert secret_steps == ['Push release refs', 'Open release pull request']
for name in ['Bump version', 'Commit and tag release locally', 'Generate NEWS.md',
             'Post-process NEWS.md', 'Fold NEWS.md into the release commit']:
    assert "inputs.release-mode != 'publish'" in steps[name]['if']
assert "inputs.release-mode != 'prepare-pr'" in release['jobs']['publish']['if']
assert steps['Push release refs']['if'] == '${{ !inputs.dry-run }}'
assert steps['Open release pull request']['if'] == "${{ !inputs.dry-run && inputs.release-mode == 'prepare-pr' }}"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bare = root / 'origin.git'
    repo = root / 'repo'
    repo.mkdir()
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    # Network calls are mocked; ref updates use a real local Git remote.
    gh = bin_dir / 'gh'
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RUNNER_TEMP/gh-calls"\n')
    gh.chmod(0o755)
    assert run(['git', 'init', '--bare', '-q', str(bare)]).returncode == 0

    def git(*args):
        result = run(['git', *args], cwd=repo)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    git('init', '-qb', 'main')
    git('config', 'user.email', 'test@example.org')
    git('config', 'user.name', 'Test Author')
    git('remote', 'add', 'origin', str(bare))
    git('commit', '--allow-empty', '-qm', 'ci: initial')
    initial = git('rev-parse', 'HEAD')
    git('push', '-q', 'origin', 'main')
    env = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}', RUNNER_TEMP=tmp,
               VERSION='1.2.3', PACKAGE='example', VERSION_TYPE='patch', NOTES_MODE='autonewsmd',
               DRY_RUN='false', RELEASE_MODE='prepare-pr', GITHUB_REF='refs/heads/main',
               GITHUB_REPOSITORY='test/example')

    def shell(name, expected=0):
        result = run(['bash', '-eu', '-o', 'pipefail', '-c', steps[name]['run']], cwd=repo, env=env)
        assert result.returncode == expected, (name, result.stdout, result.stderr)
        return result

    for mode in ['direct', 'prepare-pr', 'publish']:
        env['RELEASE_MODE'] = mode
        shell('Validate inputs and ref')
    env['RELEASE_MODE'] = 'bad'
    shell('Validate inputs and ref', 1)
    env.update(RELEASE_MODE='prepare-pr', GITHUB_REF='refs/pull/1/merge')
    shell('Validate inputs and ref', 1)
    env['DRY_RUN'] = 'true'
    shell('Validate inputs and ref')
    env.update(DRY_RUN='false', GITHUB_REF='refs/heads/main')
    shell('Validate release tag')
    (repo / 'DESCRIPTION').write_text('Package: example\nVersion: 1.2.3\n')
    git('add', 'DESCRIPTION')
    shell('Commit and tag release locally')
    prepared = git('rev-parse', 'HEAD')
    assert '[skip ci]' not in git('log', '-1', '--format=%s')
    shell('Push release refs')
    assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == initial
    assert git('ls-remote', 'origin', 'refs/heads/release/v1.2.3').split()[0] == prepared
    assert git('ls-remote', 'origin', 'refs/tags/v1.2.3') == ''
    shell('Open release pull request')
    assert '--head release/v1.2.3 --title chore: release v1.2.3' in (root / 'gh-calls').read_text()
    assert '[x] User docs' in (root / 'release-pr.md').read_text()
    # Simulate merging the reviewed release PR, then publish without moving main.
    git('push', '-q', 'origin', 'main')
    env['RELEASE_MODE'] = 'publish'
    shell('Push release refs')
    assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == prepared
    assert git('ls-remote', 'origin', 'refs/tags/v1.2.3').split()[0] == prepared
    shell('Validate release tag')
    shell('Push release refs')  # Publishing can recover after a successful tag push.
    env['RELEASE_MODE'] = 'direct'
    shell('Validate release tag', 1)
    env['RELEASE_MODE'] = 'publish'
    git('commit', '--allow-empty', '-qm', 'ci: later change')
    shell('Validate release tag', 1)  # Never move a version tag to another commit.
    # Atomic direct pushes leave main unchanged if the tag update is rejected.
    env['RELEASE_MODE'] = 'direct'
    git('tag', '-f', 'v1.2.3')
    result = run(['bash', '-eu', '-o', 'pipefail', '-c', steps['Push release refs']['run']], cwd=repo, env=env)
    assert result.returncode != 0
    assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == prepared
print('Release ref and credential regression checks passed')
