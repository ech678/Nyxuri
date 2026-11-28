.pragma library

// D4f bar appearance starter presets ("外形起点"): replaces the retired
// cornerStyle 0..5 enum as write-only axis recipes (D-7). Applying a preset
// writes only its style/edge axes onto the bar entry and never persists a
// preset name; the UI highlights whichever recipe matches the live axes.

var ORDER = ["hug", "floating", "islands", "material", "materialHug", "panel"];

var PRESETS = {
    hug: {
        backplate: true,
        lanePill: false,
        tint: false,
        edgeMargin: 0,
        squareCorners: false,
        capsuleRadius: "pill",
        groupColor: "layer1"
    },
    floating: {
        backplate: true,
        lanePill: false,
        tint: false,
        edgeMargin: 5,
        squareCorners: false,
        capsuleRadius: "pill",
        groupColor: "layer1"
    },
    islands: {
        backplate: false,
        lanePill: false,
        tint: false,
        edgeMargin: 0,
        squareCorners: false,
        capsuleRadius: "pill",
        groupColor: "layer0"
    },
    material: {
        backplate: false,
        lanePill: true,
        tint: true,
        edgeMargin: 5,
        squareCorners: false,
        capsuleRadius: "pill",
        groupColor: "layer1"
    },
    materialHug: {
        backplate: false,
        lanePill: true,
        tint: true,
        edgeMargin: 0,
        squareCorners: false,
        capsuleRadius: "pill",
        groupColor: "layer1"
    },
    panel: {
        backplate: true,
        lanePill: false,
        tint: false,
        edgeMargin: 0,
        squareCorners: true,
        capsuleRadius: "rounded",
        groupColor: "layer1"
    }
};

function values(key) {
    const preset = PRESETS[key];
    return preset ? Object.assign({}, preset) : null;
}

function currentPreset(axes) {
    if (!axes)
        return "";
    for (let i = 0; i < ORDER.length; i += 1) {
        const key = ORDER[i];
        const preset = PRESETS[key];
        let matched = true;
        for (const prop in preset) {
            if (axes[prop] !== preset[prop]) {
                matched = false;
                break;
            }
        }
        if (matched)
            return key;
    }
    return "";
}
