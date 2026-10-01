.pragma library

function desktopId(value) {
    const id = String(value || "").trim();
    return id.endsWith(".desktop") ? id.slice(0, -8) : id;
}

// MPRIS identifies applications, not individual windows or browser tabs.
function matchingPlayers(players, applicationId) {
    const id = desktopId(applicationId);
    return id ? Array.from(players).filter(player => player && desktopId(player.desktopEntry) === id) : [];
}

function selectPlayer(matches, current) {
    return matches.indexOf(current) >= 0 ? current : matches.length ? matches[0] : null;
}
