#!/usr/bin/env bash
# Compile every unit fragment shader (plugins/*/shaders/frag/*.frag) into its
# committed .qsb next to the source. Run after editing any .frag; the shell
# loads precompiled qsb at runtime (see development.md).

set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)

if command -v qsb >/dev/null 2>&1; then
    qsb_command=$(command -v qsb)
else
    qt_paths_command=""
    if command -v qtpaths6 >/dev/null 2>&1; then
        qt_paths_command=$(command -v qtpaths6)
    elif command -v qtpaths >/dev/null 2>&1; then
        qt_paths_command=$(command -v qtpaths)
    fi
    qsb_command=""
    if [[ -n "$qt_paths_command" ]]; then
        qt_libexec=$($qt_paths_command --query QT_HOST_LIBEXECS 2>/dev/null || true)
        qt_bins=$($qt_paths_command --query QT_INSTALL_BINS 2>/dev/null || true)
        if [[ -n "$qt_libexec" && -x "$qt_libexec/qsb" ]]; then
            qsb_command=$qt_libexec/qsb
        elif [[ -n "$qt_bins" && -x "$qt_bins/qsb" ]]; then
            qsb_command=$qt_bins/qsb
        fi
    fi
    if [[ -z "$qsb_command" ]] && command -v pkg-config >/dev/null 2>&1 \
        && pkg-config --exists Qt6Core; then
        qt_libexec=$(pkg-config --variable=libexecdir Qt6Core)
        if [[ -x "$qt_libexec/bin/qsb" ]]; then
            qsb_command=$qt_libexec/bin/qsb
        fi
    fi
    if [[ -z "$qsb_command" ]]; then
        echo "Qt Shader Tools qsb was not found" >&2
        exit 1
    fi
fi

built=0
while IFS= read -r -d '' frag; do
    frag_dir=$(dirname -- "$frag")
    output_dir="$frag_dir/../qsb"
    output_file="$output_dir/$(basename -- "$frag").qsb"
    mkdir -p -- "$output_dir"
    "${qsb_command}" --qt6 -o "${output_file}" "${frag}"
    echo "Built ${output_file#"${project_dir}/"}"
    built=$((built + 1))
done < <(find "${project_dir}/units" -path '*/shaders/frag/*.frag' -print0 | sort -z)

if [[ "$built" -eq 0 ]]; then
    echo "No fragment shaders found under plugins/*/shaders/frag" >&2
    exit 1
fi
echo "Compiled ${built} shader(s)"
