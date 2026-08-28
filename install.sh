#!/usr/bin/env bash

# ==============================================================================
# NyxNiri — Noctalia & Niri Dotfiles Installer Bootstrap
# Lightweight Bash bootstrap wrapper for local execution and curl pipelines.
# Hands over execution to the native Python engine (nyxniri).
# ==============================================================================

set -euo pipefail

# --- ANSI palette (mirrors nyxniri/constants.py:Colors; single source of style) ---
RED=$'\033[1;31m'; GRN=$'\033[1;32m'; YEL=$'\033[1;33m'; BLU=$'\033[1;34m'; OFF=$'\033[0m'

# --- Bilingual helper: bootstrap runs before Python i18n, so sniff $LANG/$LC_ALL ---
_lang_is_zh() { [[ "${LANG:-}${LC_ALL:-}" == *zh* ]]; }
# say "zh text" "en text" -> prints zh when locale is Chinese, else en.
say() { if _lang_is_zh; then printf '%s' "$1"; else printf '%s' "${2:-$1}"; fi; }

CACHE_DIR="$HOME/.cache/NyxNiri"
BOOTSTRAP_URL="https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh"

GIT_MIRROR_REGISTRY=(
    "Official|https://github.com/ech678/NyxNiri.git"
    "gh-proxy.org|https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"
)

# NYXNIRI_REPO: 指定后单源直连(不回退官方),服务 fork 与内网镜像场景
if [ -n "${NYXNIRI_REPO:-}" ]; then
    case "$NYXNIRI_REPO" in
        https://*|git@*|ssh://*)
            GIT_MIRROR_REGISTRY=("Custom|${NYXNIRI_REPO}")
            ;;
        *)
            printf '%s[✗] %s%s\n' "$RED" \
                "$(say "NYXNIRI_REPO 指定的地址不受支持: ${NYXNIRI_REPO}" "Unsupported NYXNIRI_REPO address: ${NYXNIRI_REPO}")" \
                "$OFF" >&2
            printf '  %s\n' "$(say "仅接受 https:// 、 git@ 、 ssh:// 开头的仓库地址。" "Only https:// , git@ , ssh:// addresses are accepted.")" >&2
            exit 1
            ;;
    esac
fi

git_clone_timeout() {
    local url="$1" target_dir="$2"
    local git_args=(clone)
    if [ -t 2 ]; then
        git_args+=(--progress)
    fi
    git_args+=(-c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 --depth 1 "$url" "$target_dir")
    env GIT_TERMINAL_PROMPT=0 git "${git_args[@]}"
}

clone_repo_bootstrap() {
    local target_dir="$1"
    printf '%s:: %s%s\n' "$BLU" "$(say "拉取仓库至缓存 ($target_dir)…" "Pulling repository to cache ($target_dir)…")" "$OFF" >&2

    local idx=1
    for item in "${GIT_MIRROR_REGISTRY[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"

        printf '  [%d/%d] %s\n' "$idx" "${#GIT_MIRROR_REGISTRY[@]}" \
            "$(say "从 [$tag] 节点拉取…" "Pulling from [$tag]…")" >&2

        if [ "$target_dir" = "$CACHE_DIR" ] && [[ "$target_dir" == "$HOME/"* ]]; then
            rm -rf "$target_dir" 2>/dev/null || true
        fi

        if git_clone_timeout "$url" "$target_dir"; then
            printf '%s[✓] %s%s\n\n' "$GRN" "$(say "已从 [$tag] 拉取" "Pulled from [$tag]")" "$OFF" >&2
            return 0
        fi
        idx=$((idx + 1))
    done

    printf '%s[✗] %s%s\n' "$RED" "$(say "所有镜像节点均拉取失败。请检查网络。" "All mirror nodes failed. Please check network.")" "$OFF" >&2
    return 1
}

exec_python_engine() {
    local target_dir="$1"
    shift

    cd -- "$target_dir" || return 1
    # -I -S blocks PYTHON* and sitecustomize startup injection; the fixed
    # launcher receives the validated tree and user arguments separately.
    local python_launcher='import sys; target = sys.argv.pop(1); sys.path.insert(0, target); sys.argv[0] = "nyxniri"; from nyxniri.cli import main; main()'

    # Only reconnect to /dev/tty if stdin is piped (e.g. curl | bash) AND no subcommand args are given
    if [ "$#" -eq 0 ] && [ ! -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; then
        exec python3 -I -S -c "$python_launcher" "$target_dir" "$@" < /dev/tty
    else
        exec python3 -I -S -c "$python_launcher" "$target_dir" "$@"
    fi
}

engine_is_complete() {
    local target_dir="$1"
    local module
    [ -f "$target_dir/install.sh" ] || return 1
    # Top-level engine modules (infrastructure + entrypoints, §13)
    for module in __init__ __main__ cli constants core deps doctor i18n network tui; do
        [ -f "$target_dir/nyxniri/$module.py" ] || return 1
    done
    # deploy/ subpackage (atomic · manifest · templates · assets · hardware · preset · deploy)
    for module in __init__ atomic assets deploy hardware manifest preset templates; do
        [ -f "$target_dir/nyxniri/deploy/$module.py" ] || return 1
    done
    # state/ subpackage (backup · uninstall)
    for module in __init__ backup uninstall; do
        [ -f "$target_dir/nyxniri/state/$module.py" ] || return 1
    done
    # modules/ subpackage (fcitx · fisher · greeter · gtktheme)
    for module in __init__ fcitx fisher greeter gtktheme; do
        [ -f "$target_dir/nyxniri/modules/$module.py" ] || return 1
    done
    [ -f "$target_dir/configs/niri/config.kdl" ] \
        && [ -f "$target_dir/configs/noctalia/noctalia-config.toml" ] \
        && [ -f "$target_dir/configs/fish/config.fish" ] \
        && [ -d "$target_dir/assets/wallpapers" ] \
        && [ -d "$target_dir/assets/fcitx5" ]
}

legacy_tree_detected() {
    local target_dir="$1"
    [ -f "$target_dir/lib/main.sh" ] \
        && [ -d "$target_dir/v2" ] \
        && [ ! -d "$target_dir/nyxniri" ]
}

show_legacy_migration() {
    # Migration is critical and the actionable curl command must always show,
    # so this block intentionally prints both languages rather than sniffing $LANG.
    local target_dir="$1"
    printf '\n%s[!] Legacy Bash checkout detected: %s%s\n' "$YEL" "$target_dir" "$OFF" >&2
    printf '%s\n' \
        '    The old "nyxniri update" cannot switch to the current Python layout.' \
        '    Run the current bootstrap instead:' \
        '' \
        "      curl -fsSL --connect-timeout 10 $BOOTSTRAP_URL | bash" \
        '' \
        '    Existing configs and snapshots under ~/.config are kept.' \
        '' >&2
    printf '%s[!] 检测到旧版 Bash 仓库。旧版 "nyxniri update" 无法直接迁移到新版目录。%s\n' "$YEL" "$OFF" >&2
    printf '%s\n\n' '    请运行上面的新版引导；~/.config 下的现有配置与快照不会被删除。' >&2
}

main() {
    # 1. Prevent running as root
    if [ "$(id -u)" -eq 0 ]; then
        printf '\n%s[✗] %s%s\n\n' "$RED" \
            "$(say "请勿以 root 运行，使用普通用户重新执行: ./install.sh" "Do not run as root. Re-run as normal user: ./install.sh")" \
            "$OFF" >&2
        exit 1
    fi

    # 2. Determine script location and stop legacy checkouts before bootstrapping.
    local real_script="" script_dir=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        real_script="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
        script_dir="$(cd "$(dirname "$real_script")" 2>/dev/null && pwd)"
    fi
    if [ -n "$script_dir" ] && legacy_tree_detected "$script_dir"; then
        show_legacy_migration "$script_dir"
        exit 2
    fi

    # 3. Check for python3
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s[✗] %s%s\n' "$RED" \
            "$(say "未找到 python3，请先安装 Python 3.11+。" "python3 is required but missing. Please install Python 3.11+ first.")" \
            "$OFF" >&2
        exit 1
    fi
    local python_version py_major py_minor
    python_version="$(python3 -I -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')" || {
        printf '%s[✗] %s%s\n' "$RED" \
            "$(say "无法确定 Python 版本，请安装 Python 3.11+。" "Could not determine the Python version. Please install Python 3.11+.")" \
            "$OFF" >&2
        exit 1
    }
    IFS=. read -r py_major py_minor <<< "$python_version"
    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 11 ]; }; then
        printf '%s[✗] %s%s\n' "$RED" \
            "$(say "需要 Python 3.11+（当前 $python_version），请升级后重试。" "Python 3.11+ is required (found $python_version). Please upgrade python3 and retry.")" \
            "$OFF" >&2
        exit 1
    fi

    # 4. Local repository execution
    if [ -n "$script_dir" ] \
        && { [ -d "$script_dir/nyxniri" ] || [ -d "$script_dir/configs" ] || [ -d "$script_dir/assets" ]; }; then
        if ! engine_is_complete "$script_dir"; then
            printf '%s[✗] %s: %s%s\n' "$RED" "$(say "NyxNiri 源码不完整" "NyxNiri source is incomplete")" "$script_dir" "$OFF" >&2
            printf '    %s\n' "$(say "请恢复或重新克隆仓库后再运行 ./install.sh。" "Restore or clone the repository again, then rerun ./install.sh.")" >&2
            exit 1
        fi
        exec_python_engine "$script_dir" "$@"
    fi

    # 5. Standalone / Cache execution
    if ! command -v git >/dev/null 2>&1; then
        printf '%s[✗] %s%s\n' "$RED" \
            "$(say "未找到 git，请先安装。" "git is missing. Please install git first.")" \
            "$OFF" >&2
        exit 1
    fi

    local cache_update_failed=0
    if [ -d "$CACHE_DIR/.git" ] && ! engine_is_complete "$CACHE_DIR"; then
        printf '%s[!] %s%s\n' "$YEL" \
            "$(say "缓存源码不完整，正在重建…" "Cached source is incomplete; rebuilding it…")" \
            "$OFF" >&2
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    elif [ ! -d "$CACHE_DIR/.git" ]; then
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    else
        printf '%s:: %s%s\n' "$BLU" "$(say "更新缓存仓库…" "Updating cache repository…")" "$OFF" >&2
        if [ -t 2 ]; then
            git -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 -c http.connectTimeout=10 -c http.timeout=20 -C "$CACHE_DIR" pull --ff-only --progress || cache_update_failed=1
        else
            git -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 -c http.connectTimeout=10 -c http.timeout=20 -C "$CACHE_DIR" pull --ff-only --quiet >/dev/null 2>&1 || cache_update_failed=1
        fi
        if [ "$cache_update_failed" -eq 1 ]; then
            printf '%s[!] %s%s\n' "$YEL" \
                "$(say "缓存更新失败，继续使用上一次的完整副本。" "Cache update failed; continuing with the last complete copy.")" \
                "$OFF" >&2
        fi
    fi

    if engine_is_complete "$CACHE_DIR"; then
        exec_python_engine "$CACHE_DIR" "$@"
    else
        printf '%s[✗] %s: %s%s\n' "$RED" "$(say "缓存源码仍不完整" "Cached source is still incomplete")" "$CACHE_DIR" "$OFF" >&2
        printf '    %s\n' "$(say "请检查网络后重新运行引导。" "Check the network, then run the bootstrap again.")" >&2
        exit 1
    fi
}

main "$@"
