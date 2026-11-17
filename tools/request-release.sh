#!/usr/bin/env bash
# Usage: request-release.sh VERSION SUMMARY TEST_SUMMARY [-- TEST_COMMAND ARG...]
# Ship this file beside release_request.py. No host credentials or signing keys.
set -euo pipefail
umask 077
[[ $# -ge 3 ]] || { printf 'Usage: request-release.sh VERSION SUMMARY TEST_SUMMARY [-- TEST_COMMAND ARG...]\n' >&2; exit 2; }
version=$1; summary=$2; tests=$3; shift 3
service=${K12_SERVICE:-hello}
repository=${K12_REPOSITORY:-shotgun1107/k12-hello}
helper=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(git rev-parse --show-toplevel)
cd -- "$root"
[[ $(git symbolic-ref --short HEAD) == main ]]
[[ -z $(git status --porcelain) ]]
remote=$(git remote get-url --push origin)
python3 -B - "$remote" "$repository" <<'PY'
import re,sys,urllib.parse
remote,repo=sys.argv[1:]
if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) is None: raise SystemExit(1)
if '://' in remote:
    u=urllib.parse.urlsplit(remote)
    ok=u.scheme in ('https','ssh') and u.hostname=='github.com' and u.path.removeprefix('/').removesuffix('.git')==repo
else:
    ok=re.fullmatch(r'git@[A-Za-z0-9._-]+:'+re.escape(repo)+r'(?:\.git)?',remote) is not None
if not ok: raise SystemExit(1)
PY
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
commit=$(git rev-parse HEAD)
[[ $commit == "$(git rev-parse refs/remotes/origin/main)" ]]
message=$(mktemp)
trap 'rm -f -- "$message"' EXIT
# Validate before running tests or creating a Git object.
python3 -B - "$helper" "$version" "$summary" "$tests" "$service" "$message" <<'PY'
import sys,json
sys.path.insert(0,sys.argv[1])
from release_request import validate
_,_,version,summary,tests,service,path=sys.argv
obj=dict(schema=1,service=service,version=version,summary=summary,tests=tests,requester='k12-dev-ai')
raw=(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')
validate(raw,'release-request/'+version,service)
with open(path,'wb') as f: f.write(raw)
PY
if [[ $# -gt 0 ]]; then
    [[ $1 == -- && $# -gt 1 ]]; shift
    "$@"
else
    python3 -B -m unittest discover -v
fi
[[ -z $(git status --porcelain) && $commit == "$(git rev-parse HEAD)" ]]
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
[[ $commit == "$(git rev-parse refs/remotes/origin/main)" ]]
tag="release-request/$version"
# Refuse existing tags locally or remotely; do not delete/overwrite a failed request.
if git show-ref --verify --quiet "refs/tags/$tag"; then exit 1; fi
[[ -z $(git ls-remote --tags origin "refs/tags/$tag") ]]
git -c tag.gpgSign=false tag -a --cleanup=verbatim -F "$message" "$tag" "$commit"
git push --porcelain origin "refs/tags/$tag:refs/tags/$tag"
printf 'Release request pushed: %s (human approval still required).\n' "$tag"
