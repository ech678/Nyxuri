complete -c nyxuri -f -n "__fish_use_subcommand" -a install   -d "Deploy dotfiles & deps (full|config)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a deploy    -d "Alias: install"
complete -c nyxuri -f -n "__fish_use_subcommand" -a snapshot  -d "Create or delete config snapshots"
complete -c nyxuri -f -n "__fish_use_subcommand" -a backup    -d "Alias: snapshot"
complete -c nyxuri -f -n "__fish_use_subcommand" -a rollback  -d "Restore config from a snapshot"
complete -c nyxuri -f -n "__fish_use_subcommand" -a restore   -d "Alias: rollback"
complete -c nyxuri -f -n "__fish_use_subcommand" -a on        -d "Enable a unit (dependency closure + package disclosure)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a enable    -d "Alias: on"
complete -c nyxuri -f -n "__fish_use_subcommand" -a off       -d "Disable a unit (customs to Vault, living area wiped)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a disable   -d "Alias: off"
complete -c nyxuri -f -n "__fish_use_subcommand" -a list      -d "List units (inventory or one detail)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a snapshot  -d "Create, list or delete config snapshots"
complete -c nyxuri -f -n "__fish_use_subcommand" -a uninstall -d "Uninstall (standard|restore|purge)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a remove    -d "Alias: uninstall"
complete -c nyxuri -f -n "__fish_use_subcommand" -a purge     -d "Deep purge everything"
complete -c nyxuri -f -n "__fish_use_subcommand" -a doctor    -d "Unit audit (Synced/Drifted/Ghost) + system checkup"
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
complete -c nyxuri -f -n "__fish_use_subcommand" -a use       -d "Switch a plugin's form (whole axis or slot axis)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a preset    -d "Deprecated alias: use"
complete -c nyxuri -f -n "__fish_use_subcommand" -a theme     -d "Switch theme (toggle|dark|light|sync|status)"
complete -c nyxuri -f -n "__fish_use_subcommand" -a bug       -d "Generate bug report"
complete -c nyxuri -f -n "__fish_use_subcommand" -a report    -d "Alias: bug"
complete -c nyxuri -f -n "__fish_use_subcommand" -a test      -d "Sandbox deploy test"
complete -c nyxuri -f -n "__fish_use_subcommand" -a shell     -d "Shell backend (get|set|switch|status)"
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

complete -c nyxuri -f -n "__fish_seen_subcommand_from snapshot backup" -a list   -d "List snapshots"
complete -c nyxuri -f -n "__fish_seen_subcommand_from snapshot backup" -a delete -d "Delete a snapshot"

complete -c nyxuri -f -n "__fish_seen_subcommand_from on enable; and not __fish_seen_subcommand_from --form" -l form -r -d "Enable with a specific form"
complete -c nyxuri -f -n "__fish_seen_subcommand_from on enable" -l preset -r -d "Deprecated alias: --form"
complete -c nyxuri -f -n "__fish_seen_subcommand_from off disable" -l cascade -d "Also disable enabled dependents"

complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a standard -d "Standard uninstall"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a restore  -d "Uninstall and restore backup"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -a purge    -d "Deep purge everything"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -l all      -d "Alias: purge"
complete -c nyxuri -f -n "__fish_seen_subcommand_from uninstall remove" -l safe     -d "Alias: standard"

complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a core      -d "Core dependencies menu"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a apps      -d "Recommended apps menu"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a opt       -d "Alias: apps"
complete -c nyxuri -f -n "__fish_seen_subcommand_from deps" -a optional -d "Alias: apps"

complete -c nyxuri -f -n "__fish_seen_subcommand_from shell" -a "get set switch status"
complete -c nyxuri -f -n "__fish_seen_subcommand_from shell; and __fish_seen_subcommand_from set switch" -a "noctalia nyxuri-shell"

complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l force      -d "Update and force redeploy"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l deploy     -d "Alias: force"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l no-deploy  -d "Update source only"
complete -c nyxuri -f -n "__fish_seen_subcommand_from update" -l to         -d "Update to specific tag or commit"

complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a list   -d "List forms (status)"
complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a slots  -d "List slot axes and variants"
complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a slot   -d "Switch a slot axis variant"
complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a save   -d "Save current config as a user form"
complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a edit   -d "Edit a user form"
complete -c nyxuri -f -n "__fish_seen_subcommand_from use" -a delete -d "Delete a user form"
complete -c nyxuri -f -n "__fish_seen_subcommand_from preset" -a list   -d "Deprecated alias: use list"

# whole-axis value always offers the reset target
complete -c nyxuri -f -n "__fish_seen_subcommand_from use preset" -a default -d "Reset to default form"

function __nyxuri_snapshot_indices
    set -l dirs
    for base in "$HOME/.config/nyxuri/backups"
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
