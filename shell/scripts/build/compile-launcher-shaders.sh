#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd -- "${script_dir}/../.." && pwd)
source_file="${project_dir}/assets/shaders/launcher/frag/spotlight_mode_field.frag"
output_dir="${project_dir}/assets/shaders/launcher/qsb"
output_file="${output_dir}/spotlight_mode_field.frag.qsb"

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

mkdir -p -- "${output_dir}"
"${qsb_command}" --qt6 -o "${output_file}" "${source_file}"
echo "Built ${output_file}"
