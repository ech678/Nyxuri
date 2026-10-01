function clamp01(value) {
    return Math.max(0, Math.min(1, Number(value) || 0));
}

function supportsParallaxCanvas(preserveAspectCrop, source,
                                 sourceIsColor) {
    return !!preserveAspectCrop
        && String(source || "") !== ""
        && !sourceIsColor;
}

function parallaxCanvasGeometry(screenWidth, screenHeight,
                                preferredScale, active) {
    const safeScreenWidth = Math.max(1, Number(screenWidth) || 1);
    const safeScreenHeight = Math.max(1, Number(screenHeight) || 1);
    const safePreferredScale = active
        ? Math.max(1, Number(preferredScale) || 1) : 1;
    const scaledWidth = safeScreenWidth * safePreferredScale;
    const scaledHeight = safeScreenHeight * safePreferredScale;

    return {
        scale: safePreferredScale,
        scaledWidth: scaledWidth,
        scaledHeight: scaledHeight,
        overflowX: Math.max(0, scaledWidth - safeScreenWidth),
        overflowY: Math.max(0, scaledHeight - safeScreenHeight)
    };
}

function panoramaGeometry(screenWidth, screenHeight,
                          imageWidth, imageHeight, enabled) {
    const safeScreenWidth = Math.max(1, Number(screenWidth) || 1);
    const safeScreenHeight = Math.max(1, Number(screenHeight) || 1);
    const safeImageWidth = Math.max(0, Number(imageWidth) || 0);
    const safeImageHeight = Math.max(0, Number(imageHeight) || 0);
    const screenAspect = safeScreenWidth / safeScreenHeight;
    const imageAspect = safeImageHeight > 0
        ? safeImageWidth / safeImageHeight : 0;
    const active = !!enabled
        && safeImageWidth > 0
        && safeImageHeight > 0
        && imageAspect > screenAspect;

    if (!active) {
        return {
            active: false,
            scale: 1,
            canvasWidth: safeScreenWidth,
            canvasHeight: safeScreenHeight,
            overflowX: 0,
            overflowY: 0
        };
    }

    const scale = safeScreenHeight / safeImageHeight;
    const canvasWidth = safeImageWidth * scale;
    return {
        active: true,
        scale: scale,
        canvasWidth: canvasWidth,
        canvasHeight: safeScreenHeight,
        overflowX: Math.max(0, canvasWidth - safeScreenWidth),
        overflowY: 0
    };
}

function tiledColumnProgress(columnCount, fullSpan) {
    const columns = Math.max(0, Math.round(Number(columnCount) || 0));
    const span = Math.max(2, Math.round(Number(fullSpan) || 6));
    if (columns === 0)
        return 0.5;
    if (columns === 1)
        return 0;
    return clamp01((columns - 1) / (span - 1));
}

function isHorizontalTiledWindow(window) {
    return !!window
        && !window.isFloating
        && Number(window.layoutColumn) > 0;
}

function horizontalColumns(windows) {
    const seen = {};
    const columns = [];
    if (!windows)
        return columns;

    for (let index = 0; index < windows.length; index += 1) {
        const window = windows[index];
        if (!isHorizontalTiledWindow(window))
            continue;
        const column = Math.round(Number(window.layoutColumn));
        const key = String(column);
        if (seen[key])
            continue;
        seen[key] = true;
        columns.push(column);
    }
    columns.sort((left, right) => left - right);
    return columns;
}

function rememberFocusedHorizontalColumn(memory, focusedWindow) {
    const current = memory || {};
    if (!isHorizontalTiledWindow(focusedWindow))
        return current;

    const workspaceKey = String(focusedWindow.workspaceId || "");
    if (workspaceKey === "")
        return current;
    const column = Math.round(Number(focusedWindow.layoutColumn));
    if (Number(current[workspaceKey]) === column)
        return current;

    const next = {};
    for (let key in current)
        next[key] = current[key];
    next[workspaceKey] = column;
    return next;
}

function nearestHorizontalColumn(columns, preferredColumn) {
    if (!columns || columns.length === 0)
        return 0;

    const preferred = Number(preferredColumn);
    if (!isFinite(preferred) || preferred <= 0)
        return columns[0];

    let nearest = columns[0];
    let distance = Math.abs(nearest - preferred);
    for (let index = 1; index < columns.length; index += 1) {
        const candidateDistance =
            Math.abs(columns[index] - preferred);
        if (candidateDistance < distance) {
            nearest = columns[index];
            distance = candidateDistance;
        }
    }
    return nearest;
}

function focusedColumnProgress(columns, focusedColumn, fullSpan) {
    if (!columns || columns.length === 0)
        return 0.5;

    const resolved = nearestHorizontalColumn(
        columns, focusedColumn);
    const rankIndex = columns.indexOf(resolved);
    const span = Math.max(2, Math.round(Number(fullSpan) || 6));
    return clamp01(Math.max(0, rankIndex) / (span - 1));
}

function workspaceProgress(workspaces) {
    if (!workspaces || workspaces.length <= 1)
        return 0.5;
    let activePosition = 0;
    for (let index = 0; index < workspaces.length; index += 1) {
        if (workspaces[index].isActive) {
            activePosition = index;
            break;
        }
    }
    return clamp01(activePosition / (workspaces.length - 1));
}

function horizontalProgress(baseProgress, leftOpen, rightOpen,
                            sidebarStep) {
    let result = Number(baseProgress);
    if (!isFinite(result))
        result = 0.5;
    const step = Math.max(0, Number(sidebarStep) || 0);
    if (leftOpen)
        result -= step;
    if (rightOpen)
        result += step;
    return clamp01(result);
}

function wallpaperPosition(overflow, progress) {
    const safeOverflow = Math.max(0, Number(overflow) || 0);
    return -safeOverflow * clamp01(progress);
}

// Floating windows share the wallpaper's column progress, but have their own
// bounded travel distance. Sidebar travel stays available at both ends of the
// wallpaper crop, where horizontalProgress may already be clamped.
function floatingParallaxOffset(tiledProgress, leftOpen, rightOpen,
                                followColumns, followSidebars, distance) {
    const travel = Math.max(0, Number(distance) || 0);
    const progress = Number(tiledProgress);
    let offset = followColumns
        ? (0.5 - clamp01(isFinite(progress) ? progress : 0.5)) * travel * 2 : 0;
    if (followSidebars) {
        if (leftOpen)
            offset += travel;
        if (rightOpen)
            offset -= travel;
    }
    return offset;
}

function wallpaperToScreen(offsetX, offsetY, wallpaperX, wallpaperY) {
    return {
        x: Number(offsetX) + Number(wallpaperX),
        y: Number(offsetY) + Number(wallpaperY)
    };
}

function screenToWallpaper(offsetX, offsetY, screenX, screenY) {
    return {
        x: Number(screenX) - Number(offsetX),
        y: Number(screenY) - Number(offsetY)
    };
}

function wallpaperToNormalized(canvasWidth, canvasHeight, wallpaperX,
                               wallpaperY) {
    return {
        xNorm: clamp01(Number(wallpaperX)
            / Math.max(1, Number(canvasWidth) || 1)),
        yNorm: clamp01(Number(wallpaperY)
            / Math.max(1, Number(canvasHeight) || 1))
    };
}

function normalizedToWallpaper(canvasWidth, canvasHeight, xNorm, yNorm) {
    return {
        x: clamp01(xNorm) * Math.max(1, Number(canvasWidth) || 1),
        y: clamp01(yNorm) * Math.max(1, Number(canvasHeight) || 1)
    };
}
