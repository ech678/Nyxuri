#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH='' cd -- "${script_dir}/../.." && pwd)
cd "${repo_root}"
test_dir=${repo_root}/tests/qml
fallback_dir=${repo_root}/shared/fallback
find_runner() {
    local override=$1 candidate
    local candidates=("${override}" /usr/lib/qt6/bin/qmltestrunner qmltestrunner6 qmltestrunner-qt6 qmltestrunner)
    for candidate in "${candidates[@]}"; do
        [[ -n ${candidate} ]] || continue
        if command -v "${candidate}" >/dev/null 2>&1; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done
    return 1
}
if [[ ! -d ${test_dir} ]]; then
    printf 'test-qml: no tests/qml directory\n'
    exit 0
fi
if ! runner=$(find_runner "${QMLTESTRUNNER:-}"); then
    printf 'error: qmltestrunner required (Arch: qt6-declarative)\n' >&2
    exit 127
fi
platform=${CLAVIS_QML_TEST_PLATFORM:-offscreen}
printf 'test-qml: %s (%s)\n' "${runner}" "${platform}"
args=(-input "${test_dir}" -import "${repo_root}")
[[ ! -d ${fallback_dir} ]] || args+=(-import "${fallback_dir}")
QT_QPA_PLATFORM="${platform}" "${runner}" "${args[@]}"
