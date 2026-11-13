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

# Repository defaults must reach every R setup and renv restore on every OS.
for path in [*Path('.github/workflows').glob('*.yaml'), Path('.github/actions/r-setup/action.yaml')]:
    config = yaml.safe_load(path.read_text())
    jobs = config.get('jobs', {'composite': {'steps': config.get('runs', {}).get('steps', [])}})
    for job in jobs.values():
        for step in job.get('steps', []):
            uses = step.get('uses', '')
            if uses.startswith('r-lib/actions/setup-r@'):
                assert step['with']['cran'] == 'https://p3m.dev/cran/latest', path
                assert step['with']['use-public-rspm'] is True, path
                assert step['with']['extra-repositories'] == 'https://cloud.r-project.org', path
            if uses.startswith('r-lib/actions/setup-renv@'):
                env = {**job.get('env', {}), **step.get('env', {})}
                assert env['RENV_CONFIG_PAK_ENABLED'] == 'true', path
assert next(s for s in check['jobs']['r-cmd-check']['steps']
            if s['name'] == 'Disable parallel tests on Windows')['shell'] == 'bash'

# Source the actual copied profile, preserving an additional repository.
with tempfile.TemporaryDirectory() as tmp:
    script = Path(tmp) / 'check-profile.R'
    script.write_text('''options(repos = c(CRAN = "https://cloud.r-project.org", extra = "https://example.org"))
source("templates/config/.Rprofile")
stopifnot(
  identical(getOption("repos")[["CRAN"]], "https://p3m.dev/cran/latest"),
  identical(getOption("repos")[["extra"]], "https://example.org"),
  identical(getOption("renv.config.pak.enabled"), TRUE)
)
''')
    result = run(['Rscript', '--vanilla', str(script)])
    assert result.returncode == 0, (result.stdout, result.stderr)
print('P3M, renv/pak, and cross-platform shell regression checks passed')

# Opening a fresh clone must not invoke renv's downloading auto-loader.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / 'renv').mkdir()
    (root / 'renv.lock').write_text('{}')
    (root / 'renv/activate.R').write_text('stop("auto-loader must not run")')
    script = root / 'check-startup.R'
    script.write_text('''source(commandArgs(TRUE)[[1]])
stopifnot(!"renv" %in% loadedNamespaces())
dir.create("renv/local/fake/renv", recursive = TRUE)
writeLines("Package: renv", "renv/local/fake/renv/DESCRIPTION")
r_minor <- paste(R.version$major, strsplit(R.version$minor, ".", fixed = TRUE)[[1L]][1L], sep = ".")
writeLines(c("renv/local/fake", "another-platform", r_minor), "renv/local/startup")
source(commandArgs(TRUE)[[1]])
stopifnot(!"renv" %in% loadedNamespaces())
''')
    result = run(['Rscript', '--vanilla', str(script),
                  str(Path('templates/config/.Rprofile').resolve())], cwd=tmp)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert 'Rscript --vanilla setup.R' in result.stderr
print('Fresh-clone offline startup check passed')

# The project setup path is opt-in; callers without templates retain setup-renv.
for filename in ['r-renv-tests.yaml', 'quarto-pages.yaml']:
    config = yaml.safe_load((Path('.github/workflows') / filename).read_text())
    inputs = config[True]['workflow_call']['inputs']
    assert inputs['portable-setup']['default'] is False
    jobs = config['jobs']
    steps = next(job['steps'] for job in jobs.values() if any(
        s.get('uses', '').startswith('r-lib/actions/setup-renv@') for s in job.get('steps', [])))
    legacy = next(s for s in steps if s.get('uses', '').startswith('r-lib/actions/setup-renv@'))
    portable = next(s for s in steps if s['name'] == 'Restore portable project environment')
    assert '!inputs.portable-setup' in legacy['if']
    assert 'inputs.portable-setup' in portable['if']
    assert portable['shell'] == 'Rscript --vanilla {0}'
    assert 'R_LIBS_USER=' in portable['run']
print('Opt-in portable CI restore checks passed')

# Releases on merge: the version step reads real commit history and tags.
self_release = yaml.safe_load(Path('.github/workflows/self-release.yaml').read_text())
jobs = self_release['jobs']
assert jobs['release']['needs'] == 'checks'
assert jobs['release']['if'] == "github.ref == 'refs/heads/main'"
assert jobs['release']['permissions'] == {'contents': 'write'}
assert self_release['permissions'] == {'contents': 'read'}
assert 'secrets.RELEASE_PAT' not in str(self_release)
release_steps = {s['name']: s for s in jobs['release']['steps']}
assert release_steps['Checkout']['with']['persist-credentials'] is False
version_script = release_steps['Decide version']['run']
assert release_steps['Publish release']['if'] == "${{ steps.version.outputs.tag != '' && !inputs.dry-run }}"

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp) / 'repo'
    repo.mkdir()

    def git(*args):
        result = run(['git', *args], cwd=repo)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def commit(message, *files):
        for name in files:
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.read_text() + 'x\n' if path.exists() else 'x\n')
        git('add', '-A')
        git('commit', '--allow-empty', '-qm', message)

    def decide(bump='auto'):
        output = Path(tmp) / 'output'
        output.write_text('')
        env = dict(os.environ, BUMP=bump, GITHUB_OUTPUT=str(output), GITHUB_SHA=git('rev-parse', 'HEAD'))
        result = run(['bash', '-eu', '-o', 'pipefail', '-c', version_script], cwd=repo, env=env)
        return result, output.read_text().strip().removeprefix('tag=')

    def expect(tag, bump='auto', code=0):
        result, got = decide(bump)
        assert (result.returncode, got) == (code, tag), (tag, bump, result.stdout, result.stderr)
        return result

    git('init', '-qb', 'main')
    git('config', 'user.email', 'test@example.org')
    git('config', 'user.name', 'Test Author')
    commit('feat: first')
    expect('', code=1)  # No release tag to count from.
    git('tag', 'v1.3.0')
    expect('')  # The tag already points at HEAD.
    commit('docs: notes')
    commit('chore: housekeeping')
    commit('ci: pin caller stubs to v1.3.0', 'templates/workflows/a.yaml')
    commit('ci: self checks', '.github/workflows/self-lint.yaml', '.github/workflows/self-release.yaml')
    commit('Update README.md')
    result = expect('')  # Nothing here ships.
    assert 'Ignoring non-conventional subject: Update README.md' in result.stderr + result.stdout
    commit('ci: bump a callee', '.github/workflows/r-cmd-check.yaml')
    expect('v1.3.1')
    expect('v1.3.1', 'patch')
    expect('v1.4.0', 'minor')
    expect('v2.0.0', 'major')
    expect('', 'bogus', code=1)
    commit('ci: bump a composite action', '.github/actions/r-setup/action.yaml')
    expect('v1.3.1')
    commit('fix(api): squashed fix (#9)\n\n* feat!: folded line is not a subject\n* feat: another')
    expect('v1.3.1')  # Body lines never decide the bump.
    commit('feat: new input')
    expect('v1.4.0')
    git('tag', 'v1.4.0')
    git('tag', 'v1.4.1', 'v1.3.0')  # A stray tag elsewhere must not be reused.
    commit('fix: after the tag')
    expect('', code=1)
    git('tag', '-d', 'v1.4.1')
    git('reset', '-q', '--hard', 'v1.4.0')
    commit('feat(api)!: drop an input')
    result = expect('')
    assert 'bump=major' in result.stdout
    expect('v2.0.0', 'major')
    git('reset', '-q', '--hard', 'v1.4.0')
    commit('fix: recovered\n\nBREAKING CHANGE: removes a default')
    result = expect('')
    assert 'bump=major' in result.stdout
    git('reset', '-q', '--hard', 'v1.4.0')
    commit('perf: faster')
    expect('v1.4.1')
    commit('Merge pull request #4 from x/y')  # Merge commits are skipped.
    git('checkout', '-q', 'v1.4.0')
    git('checkout', '-qb', 'side')
    commit('feat: on a side branch')
    git('checkout', '-q', 'main')
    git('merge', '-q', '--no-ff', '-m', 'Merge pull request #5 from x/side', 'side')
    expect('v1.5.0')
print('Release version regression checks passed')

# gitleaks-action lists a PR's commits through the API, so the callee job needs pull-requests: read
# and the calling job must grant at least that; comments stay off so no write scope is needed.
gitleaks = yaml.safe_load(Path('.github/workflows/gitleaks.yaml').read_text())
callee_job = gitleaks['jobs']['gitleaks']
assert gitleaks['permissions'] == {'contents': 'read'}
assert callee_job['permissions'] == {'contents': 'read', 'pull-requests': 'read'}
scan = next(s for s in callee_job['steps'] if s['name'] == 'Run gitleaks')
assert scan['env']['GITLEAKS_ENABLE_COMMENTS'] == 'false'
stub = yaml.safe_load(Path('templates/workflows/gitleaks.yaml').read_text())
assert stub['permissions'] == {'contents': 'read'}
assert callee_job['permissions'].items() <= stub['jobs']['gitleaks']['permissions'].items()
self_gitleaks = yaml.safe_load(Path('.github/workflows/self-gitleaks.yaml').read_text())
assert self_gitleaks['jobs']['gitleaks']['permissions'] == callee_job['permissions']
print('Gitleaks permission pair and disabled comments checks passed')

# Release propagation: notify-downstream sends one dispatch per repo; track-release-pr rewrites
# pins to the upstream's latest release and never downgrades. Network calls are mocked.
notify = yaml.safe_load(Path('.github/workflows/notify-downstream.yaml').read_text())
track = yaml.safe_load(Path('.github/workflows/track-release-pr.yaml').read_text())
for wf in (notify, track):
    assert wf['permissions'] == {'contents': 'read'}
    for wf_job in wf['jobs'].values():
        assert wf_job['timeout-minutes']
        for wf_step in wf_job['steps']:
            assert '${{' not in wf_step.get('run', ''), wf_step['name']
notify_script = notify['jobs']['notify']['steps'][0]['run']
bump_step = next(s for s in track['jobs']['track']['steps'] if s.get('id') == 'bump')
assert track['jobs']['track']['steps'][0]['with']['persist-credentials'] is False
assert [s['name'] for s in track['jobs']['track']['steps'] if 'BUMP_PAT' in str(s)] == [bump_step['name'], 'Open or update the bump PR']

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    gh = bin_dir / 'gh'
    gh.write_text('''#!/bin/sh
case "$*" in
  *"/dispatches"*)
    printf '%s\\n' "$*" >> "$MOCK_CALLS"
    case "$*" in *"$MOCK_FAIL_REPO"*) echo "boom" >&2; exit 1 ;; esac
    exit 0 ;;
  *"/releases/latest"*)
    if [ -n "$MOCK_NO_RELEASE" ]; then echo "gh: Not Found (HTTP 404)" >&2; exit 1; fi
    echo "$MOCK_TAG"; exit 0 ;;
  *"/commits/"*) echo "$MOCK_SHA"; exit 0 ;;
esac
exit 1
''')
    gh.chmod(0o755)
    base_env = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}', MOCK_CALLS=str(root / 'calls'),
                    GH_TOKEN='x', MOCK_FAIL_REPO='NEVER')

    def sh(script, env, cwd=root):
        return run(['bash', '-eu', '-o', 'pipefail', '-c', script], cwd=cwd, env=env)

    calls = root / 'calls'
    env = dict(base_env, EVENT_TYPE='baseline-release', REPOSITORIES='a/one\nb/two  c/three')
    assert sh(notify_script, env).returncode == 0
    assert len(calls.read_text().splitlines()) == 3
    assert 'event_type=baseline-release' in calls.read_text()
    calls.unlink()
    result = sh(notify_script, dict(env, MOCK_FAIL_REPO='b/two'))
    assert result.returncode == 1 and 'Could not notify b/two' in result.stdout
    assert len(calls.read_text().splitlines()) == 3  # a failure does not stop the later repos
    calls.unlink()
    assert sh(notify_script, dict(env, REPOSITORIES='  \n')).returncode == 0 and not calls.exists()
    assert sh(notify_script, dict(env, EVENT_TYPE='Bad Type')).returncode == 1
    assert sh(notify_script, dict(env, REPOSITORIES='not-a-repo')).returncode == 1

    sha_old, sha_new = 'a' * 40, 'b' * 40
    desc_text = 'Package: x\nRemotes:\n    seanthimons/ComptoxR@v1.2.0,\n    other/pkg\n'
    wf_text = (f'jobs:\n  a:\n    uses: seanthimons/baseline/.github/workflows/x.yaml@{sha_old} # v2.0.0\n'
               f'  b:\n    steps:\n      - uses: seanthimons/baseline/.github/actions/r-setup@{sha_old}\n'
               '      - uses: actions/checkout@' + 'c' * 40 + ' # v7.0.1\n')

    def case(pin_type, upstream, tag, files, no_release=False):
        repo = root / f'repo-{len(list(root.glob("repo-*")))}'
        repo.mkdir()
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)
        for args in (['init', '-qb', 'main'], ['config', 'user.email', 't@e.org'], ['config', 'user.name', 'T'],
                     ['add', '-A'], ['commit', '-qm', 'ci: initial']):
            assert run(['git', *args], cwd=repo).returncode == 0
        out = repo / 'out'
        e = dict(base_env, UPSTREAM=upstream, PIN_TYPE=pin_type, MOCK_TAG=tag, MOCK_SHA=sha_new,
                 GITHUB_OUTPUT=str(out), **({'MOCK_NO_RELEASE': '1'} if no_release else {}))
        result = sh(bump_step['run'], e, cwd=repo)
        outputs = dict(l.split('=', 1) for l in out.read_text().splitlines()) if out.exists() else {}
        return result, outputs, repo

    desc = {'DESCRIPTION': desc_text}
    result, outputs, repo = case('description-remote', 'seanthimons/ComptoxR', 'v1.2.3.9000', desc)
    assert result.returncode == 0 and outputs['changed'] == 'true' and outputs['current'] == 'v1.2.0', result.stderr
    assert (repo / 'DESCRIPTION').read_text() == desc_text.replace('v1.2.0', 'v1.2.3.9000')
    result, outputs, repo = case('description-remote', 'seanthimons/ComptoxR', 'v1.2.0', desc)
    assert result.returncode == 0 and outputs == {'changed': 'false'}
    result, outputs, repo = case('description-remote', 'seanthimons/ComptoxR', 'v1.1.9', desc)  # backport release
    assert result.returncode == 0 and outputs == {'changed': 'false'}
    assert (repo / 'DESCRIPTION').read_text() == desc_text
    result, _, _ = case('description-remote', 'seanthimons/ComptoxR', 'v1.3.0', {'DESCRIPTION': 'Package: x\n'})
    assert result.returncode == 1
    result, outputs, _ = case('description-remote', 'seanthimons/ComptoxR', '', desc, no_release=True)
    assert result.returncode == 0 and outputs == {'changed': 'false'}
    result, _, _ = case('description-remote', 'seanthimons/ComptoxR', 'bad tag', desc)
    assert result.returncode == 1
    result, _, _ = case('nope', 'seanthimons/ComptoxR', 'v1.3.0', desc)
    assert result.returncode == 1

    result, outputs, repo = case('workflow-sha', 'seanthimons/baseline', 'v2.1.0',
                                 {'.github/workflows/a.yaml': wf_text, '.github/workflows/b.yml': wf_text})
    assert result.returncode == 0 and outputs['changed'] == 'true' and outputs['current'] == 'v2.0.0', result.stderr
    for name in ('a.yaml', 'b.yml'):
        text = (repo / '.github/workflows' / name).read_text()
        assert f'x.yaml@{sha_new} # v2.1.0' in text and f'r-setup@{sha_new} # v2.1.0' in text
        assert sha_old not in text and 'actions/checkout@' + 'c' * 40 + ' # v7.0.1' in text  # third-party untouched
    result, outputs, _ = case('workflow-sha', 'seanthimons/baseline', 'v1.9.0', {'.github/workflows/a.yaml': wf_text})
    assert result.returncode == 0 and outputs == {'changed': 'false'}
    result, outputs, _ = case('description-remote', 'seanthimons/ComptoxR', '1.2.0', desc)      # prefix differs only
    assert result.returncode == 0 and outputs == {'changed': 'false'}
    result, outputs, _ = case('description-remote', 'seanthimons/ComptoxR', '1.3.0', desc)       # unprefixed newer tag
    assert result.returncode == 0 and outputs['changed'] == 'true'
    result, _, _ = case('workflow-sha', 'seanthimons/baseline', 'v2.1.0', {'.github/workflows/a.yaml': 'jobs: {}\n'})
    assert result.returncode == 1

# The PR step runs against a local bare remote; only gh is mocked.
pr_step = next(s for s in track['jobs']['track']['steps'] if s['name'] == 'Open or update the bump PR')
assert 'x-access-token' not in pr_step['run']
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    # The mock answers `pr list` from env and does not run the --jq title filter; that filter is
    # not covered here.
    (bin_dir / 'gh').write_text('''#!/bin/sh
case "$*" in
  "auth setup-git") exit 0 ;;
  "pr list"*)
    case "$*" in *"--state all"*) echo "$MOCK_PR_SAME" ;; *) echo "$MOCK_PR_OPEN" ;; esac
    exit 0 ;;
  "pr create"* | "pr edit"*) printf '%s\\n' "$*" >> "$MOCK_PR_CALLS"; exit 0 ;;
esac
exit 1
''')
    (bin_dir / 'gh').chmod(0o755)
    bare = root / 'origin.git'
    assert run(['git', 'init', '--bare', '-qb', 'main', str(bare)]).returncode == 0
    seed = root / 'seed'
    seed.mkdir()
    (seed / 'DESCRIPTION').write_text(desc_text)

    def git(cwd, *args):
        result = run(['git', *args], cwd=cwd)
        assert result.returncode == 0, (args, result.stderr)
        return result.stdout.strip()

    for args in (['init', '-qb', 'main'], ['config', 'user.email', 't@e.org'], ['config', 'user.name', 'T'],
                 ['add', '-A'], ['commit', '-qm', 'ci: initial'], ['remote', 'add', 'origin', str(bare)],
                 ['push', '-q', 'origin', 'main']):
        git(seed, *args)
    calls = root / 'pr-calls'
    branch = 'chore/bump-comptoxr'

    def pr_run(tag, pr_open='', pr_same=''):
        work = root / f'work-{len(list(root.glob("work-*")))}'
        git(root, 'clone', '-q', '--depth', '1', f'file://{bare}', str(work))  # as actions/checkout does
        git(work, 'config', 'user.email', 't@e.org')
        git(work, 'config', 'user.name', 'T')
        (work / 'DESCRIPTION').write_text(desc_text.replace('v1.2.0', tag))
        e = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}', GH_TOKEN='x', UPSTREAM='seanthimons/ComptoxR',
                 PIN_TYPE='description-remote', BASE='main', TAG=tag, CURRENT='v1.2.0', RUNNER_TEMP=str(work),
                 GITHUB_REPOSITORY='test/example', MOCK_PR_CALLS=str(calls), MOCK_PR_OPEN=pr_open, MOCK_PR_SAME=pr_same)
        result = run(['bash', '-eu', '-o', 'pipefail', '-c', pr_step['run']], cwd=work, env=e)
        assert result.returncode == 0, result.stderr
        return work

    def remote_tip():
        return git(bare, 'rev-parse', '--verify', '-q', f'refs/heads/{branch}') if run(
            ['git', 'rev-parse', '--verify', '-q', f'refs/heads/{branch}'], cwd=bare).returncode == 0 else None

    def last_call():
        return calls.read_text().splitlines()[-1] if calls.exists() else ''

    def advance_main():
        (seed / f'f{len(list(seed.glob("f*")))}').write_text('x')
        git(seed, 'add', '-A')
        git(seed, 'commit', '-qm', 'ci: main moves')
        git(seed, 'push', '-q', 'origin', 'main')

    pr_run('v1.3.0')                                            # first run: branch absent -> push and create
    first = remote_tip()
    assert first and last_call().startswith('pr create') and 'bump comptoxr pin to v1.3.0' in last_call()
    calls.unlink()
    advance_main()                                              # every later case runs on a moved base
    pr_run('v1.3.0', pr_open='7', pr_same='7')                  # same release has a PR: no push, no PR call
    assert remote_tip() == first and not calls.exists()
    pr_run('v1.3.0')                                            # pushed but PR creation failed earlier: keep the branch, create the PR
    assert remote_tip() == first and last_call().startswith('pr create')
    calls.unlink()
    pr_run('v1.3.0', pr_same='7')                               # PR closed on purpose: stays closed, no re-push
    assert remote_tip() == first and not calls.exists()
    pr_run('v1.4.0', pr_open='7')                               # newer release: force-push, edit the open PR
    second = remote_tip()
    assert second != first and last_call().startswith('pr edit 7') and 'to v1.4.0' in last_call()
    calls.unlink()
    human = root / 'human'
    git(root, 'clone', '-q', '-b', branch, str(bare), str(human))
    git(human, 'config', 'user.email', 'maintainer@example.org')
    git(human, 'config', 'user.name', 'Maintainer')
    git(human, 'commit', '--allow-empty', '-qm', 'fix: adjust for the new release')
    git(human, 'push', '-q', 'origin', branch)
    human_tip = remote_tip()
    pr_run('v1.5.0', pr_open='7')                               # a maintainer's commit is never overwritten
    assert remote_tip() == human_tip and not calls.exists()
    git(bare, 'update-ref', '-d', f'refs/heads/{branch}')       # branch deleted after closing the PR
    pr_run('v1.5.0', pr_same='9')
    assert remote_tip() is None and not calls.exists()
print('Release propagation checks passed')
