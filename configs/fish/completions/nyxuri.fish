complete -c nyxuri -f -n "__fish_use_subcommand" -a install   -d "Deploy dotfiles & deps (full|config)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a deploy    -d "Alias: install"
complete -c nyxuri -f -n "__fish_use_subcommand" -a snapshot  -d "Create or delete config snapshots"
complete -c nyxuri -f -n "__fish_use_subcommand" -a backup    -d "Alias: snapshot"
complete -c nyxuri -f -n "__fish_use_subcommand" -a rollback  -d "Restore config from a snapshot"
complete -c nyxuri -f -n "__fish_use_subcommand" -a restore   -d "Alias: rollback"
complete -c nyxuri -f -n "__fish_use_subcommand" -a list      -d "List all snapshots"
complete -c nyxuri -f -n "__fish_use_subcommand" -a uninstall -d "Uninstall (standard|restore|purge)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a remove    -d "Alias: uninstall"
complete -c nyxuri -f -n "__fish_use_subcommand" -a purge     -d "Deep purge everything"
complete -c nyxuri -f -n "__fish_use_subcommand" -a doctor    -d "Run system diagnostics"
complete -c nyxuri -f -n "__fish_use_subcommand" -a clean     -d "Inspect and clean caches"
complete -c nyxuri -f -n "__fish_use_subcommand" -a pkg       -d "Shared package manager"
complete -c nyxuri -f -n "__fish_seen_subcommand_from pkg" -a "install upgrade remove search info installed"
complete -c nyxuri -f -n "__fish_seen_subcommand_from clean" -s n -l dry-run -d "Preview without deleting"
complete -c nyxuri -f -n "__fish_seen_subcommand_from clean" -l only -r -d "Run selected tasks"
complete -c nyxuri -f -n "__fish_use_subcommand" -a deps      -d "Dependency management (core|apps)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a apps      -d "Recommended apps installer"
complete -c nyxuri -f -n "__fish_use_subcommand" -a recommended -d "Alias: apps"
complete -c nyxuri -f -n "__fish_use_subcommand" -a wallpapers -d "Download wallpaper pack"
complete -c nyxuri -f -n "__fish_use_subcommand" -a wp        -d "Alias: wallpapers"
complete -c nyxuri -f -n "__fish_use_subcommand" -a preset    -d "Manage config presets"
complete -c nyxuri -f -n "__fish_use_subcommand" -a theme     -d "Switch theme (toggle|dark|light|sync|status)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a bug       -d "Generate bug report"
complete -c nyxuri -f -n "__fish_use_subcommand" -a report    -d "Alias: bug"
complete -c nyxuri -f -n "__fish_use_subcommand" -a test      -d "Sandbox deploy test"
complete -c nyxuri -f -n "__fish_use_subcommand" -a greeter   -d "Greeter (install|status|uninstall)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a fcitx     -d "Fcitx5 skin (install|status|uninstall)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a gtk       -d "GTK theme (install|status|uninstall)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a fisher    -d "Fisher plugins (install|status|uninstall)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a update    -d "Update repo & configs"
complete -c nyxuri -f -n "__fish_use_subcommand" -a help      -d "Show help"
complete -c nyxuri -f -n "__fish_use_subcommand" -a -h        -d "Alias: help"
complete -c nyxuri -f -n "__fish_use_subcommand" -a --help    -d "Alias: help"

complete -c nyxuri -f -n "__fish_seen_subcommand_from install deploy" -a full   -d "Full setup (deps + configs + optional)"
complete -c nyxuri -f -n "__fish_seen_subcommand_from install deploy" -a config -d "Configs only"

complete -c nyxuri -f -n "__fish_seen_subcommand_from theme" -a toggle -d "Toggle dark/light"
complete -c nyxuri -f -n "__fish_seen_subcommand_from theme" -a dark   -d "Switch to dark"
complete -c nyxuri -f -n "__fish_seen_subcommand_from theme" -a light  -d "Switch to light"
complete -c nyxuri -f -n "__fish_seen_subcommand_from theme" -a sync   -d "Sync to current Noctalia mode"
complete -c nyxuri -f -n "__fish_seen_subcommand_from theme" -a status -d "Show current theme"

complete -c nyxuri -f -n "__fish_seen_subcommand_from snapshot backup" -a delete -d "Delete a snapshot"

complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a standard -d "Standard uninstall"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a restore  -d "Uninstall and restore backup"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a purge    -d "Deep purge everything"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -l all      -d "Alias: purge"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -l safe     -d "Alias: standard"

complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a core      -d "Core dependencies menu"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a apps      -d "Recommended apps menu"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a opt       -d "Alias: apps"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a optional -d "Alias: apps"

complete -c nyxuri -f -n "__fish_seen_subcommand_from greeter" -a install   -d "Install Greeter"
complete -c nyxuri -f -n "__fish_seen_subcommand_from greeter" -a status    -d "Show Greeter status"
complete -c nyxuri -f -n "__fish_seen_subcommand_from greeter" -a uninstall -d "Uninstall Greeter"
complete -c nyxuri -f -n "__fish_seen_subcommand_from greeter" -a setup     -d "Alias: install"
complete -c nyxuri -f -n "__fish_seen_subcommand_from greeter" -a remove    -d "Alias: uninstall"

complete -c nyxuri -f -n "__fish_seen_subcommand_from fcitx" -a install   -d "Install skin"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fcitx" -a status    -d "Show skin status"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fcitx" -a uninstall -d "Uninstall skin"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fcitx" -a setup     -d "Alias: install"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fcitx" -a remove    -d "Alias: uninstall"

complete -c nyxuri -f -n "__fish_seen_subcommand_from gtk" -a install   -d "Install GTK theme"
complete -c nyxuri -f -n "__fish_seen_subcommand_from gtk" -a status    -d "Show GTK theme status"
complete -c nyxuri -f -n "__fish_seen_subcommand_from gtk" -a uninstall -d "Uninstall GTK theme"
complete -c nyxuri -f -n "__fish_seen_subcommand_from gtk" -a setup     -d "Alias: install"
complete -c nyxuri -f -n "__fish_seen_subcommand_from gtk" -a remove    -d "Alias: uninstall"

complete -c nyxuri -f -n "__fish_seen_subcommand_from fisher" -a install   -d "Install fisher"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fisher" -a status    -d "Show fisher status"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fisher" -a uninstall -d "Uninstall fisher"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fisher" -a setup     -d "Alias: install"
complete -c nyxuri -f -n "__fish_seen_subcommand_from fisher" -a remove    -d "Alias: uninstall"

complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l force      -d "Update and force redeploy"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l deploy     -d "Alias: force"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l no-deploy  -d "Update source only"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l to         -d "Update to specific tag or commit"

complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a list   -d "List presets"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a apply  -d "Apply a preset"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a save   -d "Save current as preset"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a edit   -d "Edit a preset"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a delete -d "Delete a preset"

function __nyxuri_preset_apps
    set -l apps
    for d in "$HOME/.config"/*/
        test -d "$d/.presets"; or continue
        set -a apps (basename "$d")
    end
    if test -z "$apps"
        echo niri noctalia kitty fish
    else
        printf '%s\n' $apps
    end
end

complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from list" -a "(__nyxuri_preset_apps)" -d "App"

complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from apply" -a "(__nyxuri_preset_apps)" -d "App"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from apply" -a default -d "Reset to default"

complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from save" -a "(__nyxuri_preset_apps)" -d "App"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from edit" -a "(__nyxuri_preset_apps)" -d "App"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from delete" -a "(__nyxuri_preset_apps)" -d "App"

function __nyxuri_preset_names
    set -l app (commandline -t)
    set -l dir "$HOME/.config/$app/.presets"
    test -d "$dir"; or return
    for f in "$dir"/*
        test -f "$f"; or continue
        basename "$f" | string replace -r '\\.conf$|\\.toml$|\\.kdl$' ''
    end
end

complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from apply" -a "(__nyxuri_preset_names)" -d "Preset"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from edit" -a "(__nyxuri_preset_names)" -d "Preset"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset; and __fish_seen_subcommand_from delete" -a "(__nyxuri_preset_names)" -d "Preset"

function __nyxuri_snapshot_indices
    set -l dirs
    for base in "$HOME/.config/nyxuri/backups" "$HOME/.config/NyxNiri/backups" "$HOME/.config/nyxniri/backups"
        if test -d "$base"
            for d in "$base"/*
                switch (basename "$d")
                    case 'snapshot_*' 'pre_rollback_*'
                        test -d "$d"; and set -a dirs "$d"
                end
            end
        end
    end
    for d in "$HOME/.config"/dotfiles_backup_*
        test -d "$d"; and set -a dirs "$d"
    end
    set -l i 0
    for d in $dirs
        set i (math $i + 1)
        echo "$i"
    end
end

complete -c nyxuri -f -n "__fish_seen_subcommand_from rollback restore" -a "(__nyxuri_snapshot_indices)" -d "Snapshot index"
complete -c nyxuri -f -n "__fish_seen_subcommand_from snapshot; and __fish_seen_subcommand_from delete" -a "(__nyxuri_snapshot_indices)" -d "Snapshot index"

# Dual-track compatibility: inherit completions for legacy command name
complete -c nyxniri -w nyxuri
