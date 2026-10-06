// Pure diagnostic assembly and sanitization for the shell control plane (R11).
// No Qt object bridge, no I/O: callers pass plain values and receive a plain
// object back. The payload is built by allowlist — a field that is not named
// in buildDiagnostics() cannot leak into an export. Every string is masked
// (home directory → "~"), whitespace-collapsed and length-capped, so error
// text borrowed from external backends cannot smuggle paths or credentials.

.pragma library

var diagnosticsSchemaVersion = 1;
var maxTextCharacters = 512;
var maxErrorEntries = 12;

function maskHome(value, homePath) {
    var text = String(value === undefined || value === null ? "" : value);
    var home = String(homePath || "");
    if (home.length > 1)
        text = text.split(home).join("~");
    // Defense in depth: any residual absolute /home/<user> prefix is masked
    // as well, in case an error string embeds a path the caller never knew.
    return text.replace(/\/home\/[^\/\s"']+/g, "~");
}

function sanitizeText(value, homePath) {
    var text = maskHome(value, homePath).replace(/\s+/g, " ").trim();
    return text.slice(0, maxTextCharacters);
}

function sanitizePath(value, homePath) {
    return maskHome(value, homePath);
}

function _sanitizeError(error, homePath) {
    if (error === null || error === undefined)
        return "";
    var raw = typeof error === "object" ? (error.message !== undefined ? error.message : error.code)
                                        : error;
    return sanitizeText(raw, homePath);
}

function buildDiagnostics(input) {
    var home = String(input && input.homePath || "");
    var source = input && typeof input === "object" ? input : {};
    var payload = {
        "schemaVersion": diagnosticsSchemaVersion,
        "generatedAtMs": Math.round(Number(source.generatedAtMs) || 0),
        "shell": {
            "stage": sanitizeText(source.stage, home),
            "uptimeMs": Math.round(Number(source.uptimeMs) || 0),
            "firstFrameMs": Math.round(Number(source.firstFrameMs) || -1),
            "readyMs": Math.round(Number(source.readyMs) || -1),
            "ipcReadyMs": Math.round(Number(source.ipcReadyMs) || -1)
        },
        "compositor": {
            "present": source.compositorPresent === true,
            "connected": source.compositorConnected === true,
            "reconnecting": source.compositorReconnecting === true
        },
        "modules": [],
        "dependencies": [],
        "errors": [],
        "sampling": {
            "enabled": source.samplingEnabled === true,
            "intervalMs": Math.round(Number(source.samplingIntervalMs) || 0),
            "cpuPercent": Number(source.samplingCpuPercent) || 0,
            "rssKb": Math.round(Number(source.samplingRssKb) || 0),
            "lastSampleMs": Math.round(Number(source.samplingLastSampleMs) || 0)
        },
        "paths": {}
    };

    var modules = Array.isArray(source.modules) ? source.modules : [];
    modules.forEach(function (module) {
        if (!module || !module.id)
            return;
        payload.modules.push({
            "id": sanitizeText(module.id, home),
            "enabled": module.enabled === true,
            "state": sanitizeText(module.state, home)
        });
    });

    var dependencies = Array.isArray(source.dependencies) ? source.dependencies : [];
    dependencies.forEach(function (dependency) {
        if (!dependency || !dependency.id)
            return;
        payload.dependencies.push({
            "id": sanitizeText(dependency.id, home),
            "available": dependency.available === true,
            "probed": dependency.probed === true
        });
    });

    var errors = Array.isArray(source.errors) ? source.errors : [];
    errors.slice(0, maxErrorEntries).forEach(function (error) {
        var message = error ? _sanitizeError(error.message, home) : "";
        if (message === "")
            return;
        payload.errors.push({
            "source": sanitizeText(error.source, home),
            "message": message
        });
    });

    var paths = source.paths && typeof source.paths === "object" ? source.paths : {};
    ["config", "data", "state", "cache", "diagnostics"].forEach(function (key) {
        var value = sanitizePath(paths[key], home);
        if (value !== "")
            payload.paths[key] = value;
    });

    return payload;
}
