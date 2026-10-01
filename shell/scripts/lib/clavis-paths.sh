#!/usr/bin/env bash

# Shared XDG namespace for source-tree utility scripts.

clavis_paths_init() {
    local clavis_home=${HOME:?HOME must be set}
    local config_base=${XDG_CONFIG_HOME:-$clavis_home/.config}
    local data_base=${XDG_DATA_HOME:-$clavis_home/.local/share}
    local state_base=${XDG_STATE_HOME:-$clavis_home/.local/state}
    local cache_base=${XDG_CACHE_HOME:-$clavis_home/.cache}
    local runtime_base=${XDG_RUNTIME_DIR:-$cache_base/runtime}

    CLAVIS_CONFIG_HOME=${CLAVIS_CONFIG_HOME:-$config_base/clavis}
    CLAVIS_DATA_HOME=${CLAVIS_DATA_HOME:-$data_base/clavis}
    CLAVIS_STATE_HOME=${CLAVIS_STATE_HOME:-$state_base/clavis}
    CLAVIS_CACHE_HOME=${CLAVIS_CACHE_HOME:-$cache_base/clavis}
    CLAVIS_RUNTIME_HOME=${CLAVIS_RUNTIME_HOME:-$runtime_base/clavis}
    CLAVIS_PROFILE=${CLAVIS_PROFILE:-default}
    CLAVIS_PROFILE_CONFIG_HOME=${CLAVIS_PROFILE_CONFIG_HOME:-$CLAVIS_CONFIG_HOME/profiles/$CLAVIS_PROFILE}
    CLAVIS_PROFILE_HOME=${CLAVIS_PROFILE_HOME:-$CLAVIS_DATA_HOME/profiles/$CLAVIS_PROFILE}
    CLAVIS_GENERATED_HOME=${CLAVIS_GENERATED_HOME:-$CLAVIS_PROFILE_HOME/generated}

    export CLAVIS_CONFIG_HOME CLAVIS_DATA_HOME CLAVIS_STATE_HOME
    export CLAVIS_CACHE_HOME CLAVIS_RUNTIME_HOME CLAVIS_PROFILE
    export CLAVIS_PROFILE_CONFIG_HOME CLAVIS_PROFILE_HOME CLAVIS_GENERATED_HOME
}
