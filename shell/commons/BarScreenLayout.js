// Fork & Trim: dux-shell quickshell/Common/LayoutResolver.js (MIT).
// (references/dux-shell; D4g 批四b avoidance base + corner junction.)
// Trimmed to the Nyxuri bar topology: enabled [[bar.configs]] entries x
// screens -> per-edge band reservations and the per-bar tuck insets.
// Dropped from the original: islands/dots/free placement, connected
// frames, goth wings, docks, maximize flattening, overview stand-ins,
// displayName screens and row stacking (Nyxuri reserves an edge band by
// the largest contributing bar; a second bar on a taken edge does not
// stack rows).
//
// Corner rule (D4g 批四b author call, deviates from dux): the earliest
// configured bar (config order) meeting at a corner owns it and runs its
// full length; the later bar tucks — the shared along-axis end insets by
// the owner's band reservation plus a seam gap (dux lineage
// `config.spacing ?? 4`). Each corner adjudicates independently, so a
// bar can tuck both ends (rails on both sides outrank a top bar).
//
// Single truth: reservations arrive precomputed by the services
// projection (ScreenBarLayout) from BarGeometry.exclusiveZone — the
// exact function the bar window binds — so avoidance consumers and the
// windows cannot drift. autoHide entries reserve 0 (dux `reserves`
// lineage); their revealed position still tucks against the owner.

.pragma library

var EDGES = ["top", "bottom", "left", "right"];

var SEAM_GAP = 4;

// D4e screenList semantics: empty = every screen; a list matching no
// connected screen falls back to every screen (the same rule the window
// layer applies when multiplying entries onto screens).
function coversScreen(axes, screenName, screenNames) {
    const list = axes && Array.isArray(axes.screenList) ? axes.screenList : [];
    if (list.length === 0)
        return true;
    if (list.includes(screenName))
        return true;
    return !screenNames.some(name => list.includes(name));
}

function perpendicularEdges(edge) {
    return edge === "top" || edge === "bottom" ? ["left", "right"] : ["top", "bottom"];
}

// inputs: the enabled entries covering this screen, in config order —
//   [{id, edge, reservation}]
// reservation is the shown exclusive zone (0 for autoHide entries).
// Returns {screenName, bands, instances}:
//   bands[edge].reservation — the band's avoidance inset;
//   instances[].tuckMargins — per-bar along-axis insets the window layer
//   adds onto its own margins ({top, bottom, left, right}).
function resolveScreen(inputs, screenName) {
    const bands = {};
    for (const edge of EDGES)
        bands[edge] = {
            edge,
            reservation: 0
        };
    const instances = [];
    for (let index = 0; index < inputs.length; index += 1) {
        const input = inputs[index] || {};
        const edge = EDGES.includes(input.edge) ? input.edge : "top";
        const reservation = input.reservation > 0 ? input.reservation : 0;
        bands[edge].reservation = Math.max(bands[edge].reservation, reservation);
        instances.push({
            barId: input.id,
            edge,
            configOrder: index,
            reservation,
            tuckMargins: {
                top: 0,
                bottom: 0,
                left: 0,
                right: 0
            },
            tuckedAt: []
        });
    }
    // Corner verdict: at each corner, the earlier bar owns it; the later
    // bar insets the shared along-axis end. Both ends adjudicate
    // independently (dux manualPlacement lineage — margins encode the
    // layout, so compositor map order cannot decide it for us).
    for (const instance of instances) {
        if (instance.reservation <= 0)
            continue;
        for (const side of perpendicularEdges(instance.edge)) {
            const owner = instances.find(other => other !== instance
                && other.edge === side
                && other.reservation > 0
                && other.configOrder < instance.configOrder);
            if (!owner)
                continue;
            instance.tuckMargins[side] = bands[side].reservation + SEAM_GAP;
            instance.tuckedAt.push(side);
        }
    }
    return {
        screenName,
        bands,
        instances
    };
}

// The per-bar tuck margins for a resolved layout (0s when the bar is
// absent, owns every corner it touches, or reserves nothing).
function tuckMargins(layout, barId) {
    const empty = {
        top: 0,
        bottom: 0,
        left: 0,
        right: 0
    };
    if (!layout)
        return empty;
    const instance = layout.instances.find(instance => instance.barId === barId);
    return instance ? instance.tuckMargins : empty;
}

function reservation(layout, edge) {
    if (!layout || !EDGES.includes(edge))
        return 0;
    return layout.bands[edge].reservation;
}
