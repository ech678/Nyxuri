pragma Singleton

import QtQuick
import Quickshell
import "./SystemCardDragState.js" as DragState

Singleton {
    id: root

    // The phase is the source of truth for the gesture lifecycle.  `active`
    // and `frozen` remain as compatibility/readability aliases for the
    // existing overlay and sidebar bindings.
    readonly property string idlePhase: DragState.idle
    readonly property string draggingSidebarPhase: DragState.draggingSidebar
    readonly property string draggingPresentationPhase:
        DragState.draggingPresentation
    readonly property string frozenTransferPhase:
        DragState.frozenTransfer
    readonly property string finishingPhase: DragState.finishing
    readonly property string canceledPhase: DragState.canceled

    property string phase: root.idlePhase
    readonly property bool active: DragState.isActive(root.phase)
    readonly property bool presentationActive:
        DragState.isPresentationActive(root.phase)
    readonly property bool frozen: DragState.isFrozen(root.phase)
    readonly property bool ending: root.phase === root.finishingPhase
    readonly property bool visualHandoffPending:
        DragState.isVisualHandoffPending(
            root.phase, root.transferCommitted, root.transferPreparing)
    // Set before SystemCardService.setContainer() emits its state change.
    // This closes the small binding window in which a newly-created desktop
    // slot could otherwise become visible before the commit flag is written.
    property bool transferPreparing: false
    property bool transferCommitted: false

    property string tileId: ""
    property string screenName: ""
    property Item sourceItem: null
    property real _grabLocalX: 0
    property real _grabLocalY: 0
    readonly property real grabLocalX: root._grabLocalX
    readonly property real grabLocalY: root._grabLocalY
    property real presentationPointerX: 0
    property real presentationPointerY: 0
    property real _presentationGrabOffsetX: 0
    property real _presentationGrabOffsetY: 0
    readonly property real presentationGrabOffsetX:
        root._presentationGrabOffsetX
    readonly property real presentationGrabOffsetY:
        root._presentationGrabOffsetY
    property real ghostWidth: 0
    property real ghostHeight: 0
    property real hostWidth: 0
    property real hostHeight: 0
    readonly property real ghostX:
        root.presentationPointerX - root.presentationGrabOffsetX
    readonly property real ghostY:
        root.presentationPointerY - root.presentationGrabOffsetY
    readonly property var presentationGhostRect: ({
        x: root.ghostX,
        y: root.ghostY,
        width: root.ghostWidth,
        height: root.ghostHeight,
        valid: root.ghostWidth > 0 && root.ghostHeight > 0
    })
    property bool sourceWasBound: false

    signal canceled()
    signal handoffCheckRequested(string cardId)
    signal cancelRequested(string requestedTileId)

    function transition(nextPhase, reason) {
        if (root.phase === nextPhase)
            return;
        if (!DragState.canTransition(root.phase, nextPhase)) {
            console.warn(
                "[SystemCards] invalid drag transition",
                root.phase + " -> " + nextPhase
            );
            return;
        }
        root.phase = nextPhase;
    }

    function clearToIdle(reason) {
        // Move to idle before clearing sourceItem.  If the source was
        // destroyed, its automatic null assignment must not recursively
        // interpret this cleanup as a new cancellation.
        root.transition(root.idlePhase, reason || "reset");
        root.tileId = "";
        root.screenName = "";
        root.sourceItem = null;
        root._grabLocalX = 0;
        root._grabLocalY = 0;
        root.presentationPointerX = 0;
        root.presentationPointerY = 0;
        root._presentationGrabOffsetX = 0;
        root._presentationGrabOffsetY = 0;
        root.ghostWidth = 0;
        root.ghostHeight = 0;
        root.hostWidth = 0;
        root.hostHeight = 0;
        root.transferPreparing = false;
        root.transferCommitted = false;
        root.sourceWasBound = false;
    }

    // Begin exactly once, at the real Sidebar drag start. The source-local
    // grab point is immutable until the gesture ends.
    function begin(cardId, item, grabLocalX, grabLocalY) {
        if (root.active)
            return false;

        root.tileId = String(cardId || "");
        root.sourceItem = item;
        root.sourceWasBound = item !== null;
        root._grabLocalX = Number(grabLocalX) || 0;
        root._grabLocalY = Number(grabLocalY) || 0;
        root.transferPreparing = false;
        root.transferCommitted = false;
        root.transition(root.draggingSidebarPhase,
            "begin " + root.tileId);
        return true;
    }

    // Promote the existing gesture to the presentation host. This maps the
    // original grab point but never redefines it from the current pointer.
    function promoteToPresentation(screenName, pointerX, pointerY,
                                   presentationGrabOffsetX,
                                   presentationGrabOffsetY,
                                   width, height, hostWidth, hostHeight) {
        if (root.phase !== root.draggingSidebarPhase)
            return false;
        root.screenName = String(screenName || "");
        root.presentationPointerX = Number(pointerX) || 0;
        root.presentationPointerY = Number(pointerY) || 0;
        root._presentationGrabOffsetX =
            Number(presentationGrabOffsetX) || 0;
        root._presentationGrabOffsetY =
            Number(presentationGrabOffsetY) || 0;
        root.ghostWidth = Math.max(0, Number(width) || 0);
        root.ghostHeight = Math.max(0, Number(height) || 0);
        root.hostWidth = Math.max(1, Number(hostWidth) || 1);
        root.hostHeight = Math.max(1, Number(hostHeight) || 1);
        root.transition(root.draggingPresentationPhase,
            "promote " + root.tileId);
        return root.presentationGhostRect.valid;
    }

    function update(x, y) {
        if (!root.active || root.phase !== root.draggingPresentationPhase)
            return;
        root.presentationPointerX = Number(x) || 0;
        root.presentationPointerY = Number(y) || 0;
    }

    function freezeGhost(topLeftX, topLeftY) {
        if (root.phase !== root.draggingPresentationPhase)
            return false;
        if (isFinite(Number(topLeftX)) && isFinite(Number(topLeftY))) {
            root.presentationPointerX = Number(topLeftX)
                + root.presentationGrabOffsetX;
            root.presentationPointerY = Number(topLeftY)
                + root.presentationGrabOffsetY;
        }
        root.transition(root.frozenTransferPhase,
            "ghost frozen " + root.tileId);
        return root.presentationGhostRect.valid;
    }

    // This is called only after SystemCardService has synchronously committed
    // container=desktop.  It deliberately does not create or destroy a Card;
    // it only records that a later source teardown must never roll ownership
    // back to the sidebar.
    function markTransferCommitted(cardId) {
        const id = String(cardId || "");
        if (!root.active || id !== root.tileId)
            return false;
        if (!root.frozen)
            root.freezeGhost();
        // Keep the visual barrier continuously asserted. Setting preparing
        // false first creates a transient pending=false state before the
        // committed flag becomes visible to QML bindings.
        root.transferCommitted = true;
        root.transferPreparing = false;
        return true;
    }

    // Request the DesktopCard readiness check only after markTransferCommitted
    // has returned to its caller. Completing the handoff from an
    // onTransferCommittedChanged handler mutates the same properties while Qt
    // is still evaluating their bindings and can leave the desktop delegate
    // permanently hidden behind a stale waiting=true value.
    function requestVisualHandoffCheck(cardId) {
        const id = String(cardId || "");
        if (!root.transferCommitted || !root.visualHandoffPending
                || id !== root.tileId)
            return false;
        root.handoffCheckRequested(id);
        return true;
    }

    // Establish the visual handoff barrier before changing CardState.  The
    // desktop slot may be created synchronously by that change, but it must
    // remain hidden until its Loader has initialized the screen rect and
    // emitted handoffReady.
    function prepareVisualHandoff(cardId) {
        const id = String(cardId || "");
        if (!root.active || id !== root.tileId
                || root.transferCommitted
                || root.phase !== root.frozenTransferPhase)
            return false;
        root.transferPreparing = true;
        return true;
    }

    // Enter the finishing phase while the visual handoff barrier remains
    // active. The sidebar source may disappear before DesktopCardCanvas has
    // consumed the presentation rect; that teardown must not end this phase.
    function finishTransfer() {
        if (!root.active || !root.transferCommitted)
            return false;
        const nextPhase = DragState.finishTransfer(
            root.phase, root.transferCommitted);
        if (root.phase !== nextPhase)
            root.transition(nextPhase,
                "desktop handoff waiting " + root.tileId);
        return true;
    }

    function completeVisualHandoff(cardId) {
        const id = String(cardId || "");
        if (!root.transferCommitted || !root.visualHandoffPending
                || id !== root.tileId)
            return false;
        // clearToIdle changes the two visual-owner bindings in one QML turn:
        // the ghost becomes invisible before the DesktopCard waiting binding
        // can become visible in the next scene render.
        return root.finishGhost();
    }

    function finishGhost() {
        if (!root.active)
            return false;
        root.clearToIdle("ghost finished");
        return true;
    }

    function end() {
        if (!root.active)
            return;
        if (root.transferCommitted) {
            root.finishTransfer();
            return;
        }
        root.finishGhost();
    }

    function cancel() {
        if (!root.active)
            return false;
        // A committed transfer is final.  Late Escape/cancel callbacks may
        // clean up the visual ghost, but they must never roll state back.
        if (root.transferCommitted)
            return root.finishTransfer();

        const canceledPhase = DragState.cancel(
            root.phase, root.transferCommitted);
        root.transition(canceledPhase, "drag canceled " + root.tileId);
        root.clearToIdle("cancel complete");
        root.canceled();
        return true;
    }

    function reset() {
        if (!root.active)
            return;
        if (root.transferCommitted)
            root.finishTransfer();
        else
            root.cancel();
    }

    // SidebarHostWindow owns exclusive keyboard focus while a sidebar is
    // open.  Before commit, route Escape to DrawerView.  After commit, only
    // finish visual cleanup; never emit a rollback-capable cancel request.
    function requestCancel() {
        if (!root.active)
            return;
        if (root.transferCommitted) {
            root.finishTransfer();
            return;
        }
        root.cancelRequested(root.tileId);
    }

    onSourceItemChanged: {
        if (root.sourceItem !== null) {
            root.sourceWasBound = true;
            return;
        }
        if (!root.sourceWasBound || !root.active)
            return;

        if (root.transferCommitted) {
            // Once ownership is committed, the sidebar source lifetime is no
            // longer authoritative. The DesktopCard still has to consume the
            // presentation geometry and complete the visual handoff. In
            // particular, do not clear the phase, tileId, commit flag, or
            // presentation rect here.
            // sourceItem destruction is not handoff completion.
        } else {
            root.cancel();
        }
    }
}
