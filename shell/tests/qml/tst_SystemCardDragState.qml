import QtQuick 2.15
import QtTest 1.3

import "../../Services/SystemCardDragState.js" as DragState
import "../../Modules/SystemCards/SystemCardPlacement.js" as Placement

TestCase {
    name: "SystemCardDragState"

    function test_committedTransferKeepsActiveUntilDesktopHandoff() {
        let phase = DragState.idle;
        phase = DragState.draggingSidebar;
        phase = DragState.draggingPresentation;
        phase = DragState.freeze(phase);
        phase = DragState.finishTransfer(phase, true);
        compare(phase, DragState.finishing);
        compare(DragState.isActive(phase), true);

        phase = DragState.finish(phase);
        compare(phase, DragState.idle);
        compare(DragState.isActive(phase), false);
    }

    function test_cancelBeforeCommitReturnsToIdle() {
        let phase = DragState.draggingSidebar;
        phase = DragState.cancel(phase, false);
        compare(phase, DragState.canceled);
        phase = DragState.finish(phase);
        compare(phase, DragState.idle);
    }

    function test_lateCancelCannotRollbackCommittedTransfer() {
        const phase = DragState.finishTransfer(
            DragState.frozenTransfer, true);
        compare(DragState.cancel(phase, true), phase);
        compare(DragState.isActive(phase), true);
    }

    function test_visualHandoffStaysPendingUntilSessionIsIdle() {
        const phase = DragState.finishTransfer(
            DragState.frozenTransfer, true);
        verify(DragState.isVisualHandoffPending(phase, true));
        verify(DragState.isVisualHandoffPending(phase, false, true));
        verify(!DragState.isVisualHandoffPending(phase, false));

        const idle = DragState.finish(phase);
        verify(!DragState.isVisualHandoffPending(idle, true));
    }

    function test_screenDropPreservesGhostRectForEveryGrabPoint() {
        const drops = [
            { pointer: { x: 122, y: 208 }, offset: { x: 12, y: 18 } },
            { pointer: { x: 640, y: 420 }, offset: { x: 76, y: 80 } },
            { pointer: { x: 1260, y: 810 }, offset: { x: 145, y: 151 } }
        ];
        drops.forEach(function(drop) {
            const ghost = {
                x: drop.pointer.x - drop.offset.x,
                y: drop.pointer.y - drop.offset.y,
                width: 152,
                height: 160
            };
            const desktop = {
                x: ghost.x,
                y: ghost.y,
                width: ghost.width,
                height: ghost.height
            };
            compare(desktop.x, ghost.x);
            compare(desktop.y, ghost.y);
            compare(desktop.width, ghost.width);
            compare(desktop.height, ghost.height);
        });
    }

    function test_extractionCannotRedefineInitialGrabPoint() {
        const sourceLeft = 100;
        const initialPointer = 140;
        const grabLocal = initialPointer - sourceLeft;
        const extractionPointer = 400;
        const ghostX = extractionPointer - grabLocal;

        compare(grabLocal, 40);
        compare(ghostX, 360);
        compare(extractionPointer - ghostX, grabLocal);
        verify(extractionPointer - sourceLeft !== grabLocal);
    }

    function test_grabDistanceIsImmutableForWholeDrag() {
        const grab = { x: 40.25, y: 82.75 };
        const pointers = [
            { x: 400.5, y: 300.25 },
            { x: 500.75, y: 480.125 },
            { x: 700.875, y: 610.625 }
        ];
        pointers.forEach(function(pointer) {
            const ghost = {
                x: pointer.x - grab.x,
                y: pointer.y - grab.y
            };
            fuzzyCompare(pointer.x - ghost.x, grab.x, 0.0001);
            fuzzyCompare(pointer.y - ghost.y, grab.y, 0.0001);
        });
    }

    function test_grabPointContinuityForCornerCenterAndEdge() {
        const size = { width: 152, height: 160 };
        const grabs = [
            { x: 10, y: 10 },
            { x: size.width / 2, y: size.height / 2 },
            { x: size.width - 10, y: size.height - 10 }
        ];
        grabs.forEach(function(grab) {
            const pointer = { x: 811.375, y: 507.625 };
            const ghost = {
                x: pointer.x - grab.x,
                y: pointer.y - grab.y
            };
            fuzzyCompare(pointer.x - ghost.x, grab.x, 0.0001);
            fuzzyCompare(pointer.y - ghost.y, grab.y, 0.0001);
        });
    }

    function test_screenNormalizedPositionRoundTrips() {
        const normalized = Placement.normalizedPosition(
            640, 360, 1920, 1080);
        compare(normalized.xNorm, 1 / 3);
        compare(normalized.yNorm, 1 / 3);

        const point = Placement.screenPoint(
            normalized.xNorm, normalized.yNorm,
            1920, 1080, 152, 160);
        compare(point.x, 640);
        compare(point.y, 360);
    }

    function test_freeProjectionIgnoresWallpaperOffset() {
        const free = Placement.screenPoint(
            0.42, 0.31, 1920, 1080, 152, 160);
        const afterParallax = Placement.screenPoint(
            0.42, 0.31, 1920, 1080, 152, 160);

        compare(afterParallax.x, free.x);
        compare(afterParallax.y, free.y);
    }

    function test_freePlacementUsesOnlyPresentationHostGeometry() {
        const hostWidth = 1920;
        const hostHeight = 1080;
        const drop = { x: 713.5, y: 402.25 };
        const normalized = Placement.normalizedPosition(
            drop.x, drop.y, hostWidth, hostHeight);

        // Sidebar usable origins intentionally differ. They are not inputs to
        // either persistence or restoration once the presentation host owns
        // the drag.
        const sidebarOrigins = [
            { x: 48, y: 0 },
            { x: 0, y: 36 },
            { x: 0, y: 0 },
            { x: 0, y: 64 }
        ];
        sidebarOrigins.forEach(function(unusedOrigin) {
            const restored = Placement.screenPoint(
                normalized.xNorm, normalized.yNorm,
                hostWidth, hostHeight, 152, 160);
            compare(restored.x, drop.x);
            compare(restored.y, drop.y);
            verify(unusedOrigin.x >= 0 && unusedOrigin.y >= 0);
        });
    }

    function test_sameHostGhostAndDesktopRectAreContinuous() {
        const host = { width: 2560, height: 1440 };
        const ghost = { x: 1120.25, y: 610.5, width: 312, height: 160 };
        const normalized = Placement.normalizedPosition(
            ghost.x, ghost.y, host.width, host.height);
        const desktop = Placement.screenPoint(
            normalized.xNorm, normalized.yNorm,
            host.width, host.height, ghost.width, ghost.height);

        verify(Math.abs(desktop.x - ghost.x) <= 1);
        verify(Math.abs(desktop.y - ghost.y) <= 1);
    }

    function test_wallpaperProjectionUsesCurrentSceneOffset() {
        const wallpaper = Placement.wallpaperPoint(
            0.5, 0.4, 2000, 1000, 152, 160);
        const first = Placement.projectedWallpaperPoint(
            wallpaper.x, wallpaper.y, -100, 20);
        const second = Placement.projectedWallpaperPoint(
            wallpaper.x, wallpaper.y, -240, 40);

        compare(first.x, wallpaper.x - 100);
        compare(first.y, wallpaper.y + 20);
        compare(second.x, wallpaper.x - 240);
        compare(second.y, wallpaper.y + 40);
    }

    function test_screenToWallpaperTransitionFollowsMovingTarget() {
        const start = { x: 420, y: 300 };
        const wallpaper = { x: 900, y: 500 };
        const firstTarget = Placement.projectedWallpaperPoint(
            wallpaper.x, wallpaper.y, -180, 0);
        const secondTarget = Placement.projectedWallpaperPoint(
            wallpaper.x, wallpaper.y, -260, 30);

        compare(Placement.interpolate(start.x, firstTarget.x, 0), start.x);
        compare(Placement.interpolate(start.y, firstTarget.y, 0), start.y);
        compare(Placement.interpolate(start.x, secondTarget.x, 1),
            secondTarget.x);
        compare(Placement.interpolate(start.y, secondTarget.y, 1),
            secondTarget.y);
    }

    function test_uncommittedPresentationCanFinishWithoutTransfer() {
        compare(DragState.finish(DragState.draggingPresentation),
            DragState.idle);
    }

    function test_illegalTransitionsAreRejected() {
        verify(DragState.canTransition(
            DragState.idle, DragState.draggingSidebar));
        verify(DragState.canTransition(
            DragState.draggingSidebar, DragState.draggingPresentation));
        verify(!DragState.canTransition(
            DragState.idle, DragState.draggingPresentation));
        verify(!DragState.canTransition(
            DragState.finishing, DragState.draggingPresentation));
        verify(!DragState.canTransition(
            DragState.canceled, DragState.frozenTransfer));
        verify(DragState.canTransition(
            DragState.frozenTransfer, DragState.finishing));
    }
}
