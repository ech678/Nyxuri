#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH='' cd -- "${script_dir}/../.." && pwd)
cd "${repo_root}"
# shellcheck source=scripts/dev/files.sh
source "${script_dir}/files.sh"

scope=changed
case "${1:-}" in
    '') ;;
    --full) scope=all ;;
    --native) scope=all ;;
    -h|--help)
        printf 'Usage: %s [--full]\nDefault: changed files; --full: all lint/syntax/tests.\n' "$0"
        exit 0 ;;
    *) printf 'error: unknown option: %s\n' "$1" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2

require() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'error: %s required (Arch package: %s)\n' "$1" "$2" >&2
        exit 127
    }
}

# Keep successful output short, retain full failed diagnostics on disk.
log_dir=$(mktemp -d "${TMPDIR:-/tmp}/clavis-check.XXXXXX")
keep_logs=false
trap 'status=$?; if (( status == 0 )) && ! ${keep_logs}; then rm -rf -- "${log_dir}"; else printf "check: logs: %s\n" "${log_dir}" >&2; fi' EXIT
step() {
    local label=$1
    shift
    printf 'check: %s\n' "${label}"
    if "$@" >"${log_dir}/${label}.log" 2>&1; then
        if [[ ${label} == qml-lint ]]; then
            local warnings
            warnings=$(grep -c '^Warning:' "${log_dir}/${label}.log" || true)
            if (( warnings > 0 )); then
                printf 'check: qml-lint completed with %d advisory warnings; see log\n' "${warnings}"
                keep_logs=true
            fi
        elif [[ ${label} == tests ]]; then
            tail -n 6 "${log_dir}/${label}.log"
        fi
        return 0
    else
        local status=$?
        tail -n 60 "${log_dir}/${label}.log" >&2
        printf 'check: %s failed (exit %d)\n' "${label}" "${status}" >&2
        return "${status}"
    fi
}

step whitespace git diff --check HEAD
mapfile -d '' -t files < <(clavis_files "${scope}")
shell_files=() python_files=()
qml=false
catalog=false
for file in "${files[@]}"; do
    case ${file} in
        modules/settings/settings-routes.json|modules/settings/generated/SearchCatalog.js|modules/settings/*.qml|scripts/system/niri-actions.json|scripts/dev/generate-search-catalog.py|tests/test_search_catalog.py) catalog=true ;;
    esac
    [[ -f ${file} ]] || continue
    case ${file} in
        build/*|generated/*|third-party/*|vendor/*) continue ;;
    esac
    case ${file} in
        *.qml) qml=true ;;
        *.sh|*.sh.in|*/PKGBUILD.in|*.install) shell_files+=("${file}") ;;
        *.py) python_files+=("${file}") ;;
    esac
done
if ${qml}; then
    # Even --full avoids imposing a formatter migration on legacy QML.
    step qml-format "${script_dir}/format-qml.sh" --check
fi
if (( ${#shell_files[@]} )); then
    require shellcheck shellcheck
    for file in "${shell_files[@]}"; do bash -n "${file}"; done
    step shell-lint shellcheck -s bash -x "${shell_files[@]}"
fi
if (( ${#python_files[@]} )); then
    require python3 python
    step python-syntax python3 -c 'import pathlib, sys; [compile(pathlib.Path(p).read_bytes(), p, "exec") for p in sys.argv[1:]]' "${python_files[@]}"
fi
# Existing black-box script tests need no CMake/native build.
for test_name in niri_cursor_config manage_niri_effects matugen_registry; do
    run_test=false
    [[ ${scope} != all ]] || run_test=true
    for file in "${files[@]}"; do
        case "${test_name}:${file}" in
            niri_cursor_config:scripts/theme/write-niri-cursor-config.sh|niri_cursor_config:tests/test_niri_cursor_config.sh|\
            manage_niri_effects:scripts/system/manage-niri-effects.sh|manage_niri_effects:tests/test_manage_niri_effects.sh|\
            matugen_registry:scripts/theme/*|matugen_registry:scripts/lib/matugen-registry.sh|matugen_registry:tests/test_matugen_registry.sh|\
            *:scripts/lib/clavis-paths.sh|*:scripts/system/manage-niri-fragment.sh|*:tests/fixtures/mock-niri) run_test=true ;;
        esac
    done
    if ${run_test}; then
        if [[ ${test_name} == matugen_registry ]]; then
            require matugen matugen
            require jq jq
        fi
        step "${test_name}" bash "tests/test_${test_name}.sh"
    fi
done
if ${catalog}; then
    step search-catalog python3 "${script_dir}/generate-search-catalog.py"
    step search-catalog-contracts python3 tests/test_search_catalog.py
fi
if ${qml}; then
    lint_args=()
    [[ ${scope} != all ]] || lint_args+=(--all)
    step qml-lint "${script_dir}/lint-qml.sh" "${lint_args[@]}"
    audit_args=(--scope "${scope}" --check)
    step lifecycle-audit python3 "${script_dir}/audit-lifecycle.py" "${audit_args[@]}"
fi
if [[ ${scope} == all ]] || [[ " ${python_files[*]:-} " =~ audit-lifecycle.py ]]; then
    step lifecycle-audit-tests python3 -m unittest tests/test_lifecycle_audit.py
fi
printf 'check: passed (%s scope)\n' "${scope}"
