.pragma library

// One restrained entrance/exit language for model changes and drag removal.
var enterDuration = 240;
var exitDuration = 180;
var reflowDuration = 220;

function iconScale(presence) {
    return 0.35 + 0.65 * presence;
}
