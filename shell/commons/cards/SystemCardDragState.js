.pragma library

var idle = "idle";
var draggingSidebar = "dragging-sidebar";
var draggingPresentation = "dragging-presentation";
var frozenTransfer = "frozen-transfer";
var finishing = "finishing";
var canceled = "canceled";

function isActive(phase) {
    return String(phase || idle) !== idle;
}

function isFrozen(phase) {
    const value = String(phase || idle);
    return value === frozenTransfer || value === finishing;
}

function isPresentationActive(phase) {
    const value = String(phase || idle);
    return value === draggingPresentation
        || value === frozenTransfer
        || value === finishing;
}

function isVisualHandoffPending(phase, committed, preparing) {
    return !!(committed || preparing) && isActive(phase);
}

function canTransition(fromPhase, toPhase) {
    const from = String(fromPhase || idle);
    const to = String(toPhase || idle);
    if (from === to)
        return true;
    if (to === idle)
        return true;
    if (from === idle)
        return to === draggingSidebar;
    if (from === draggingSidebar)
        return to === draggingPresentation || to === canceled;
    if (from === draggingPresentation)
        return to === frozenTransfer || to === canceled;
    if (from === frozenTransfer)
        return to === finishing || to === canceled;
    if (from === finishing)
        return false;
    if (from === canceled)
        return false;
    return false;
}

function freeze(phase) {
    const value = String(phase || idle);
    return value === draggingPresentation ? frozenTransfer : value;
}

function finishTransfer(phase, committed) {
    const value = String(phase || idle);
    if (!committed || !isActive(value))
        return value;
    return value === frozenTransfer || value === draggingPresentation
        ? finishing : value;
}

function cancel(phase, committed) {
    const value = String(phase || idle);
    return committed ? value : (isActive(value) ? canceled : idle);
}

function finish(phase) {
    const value = String(phase || idle);
    return isActive(value) ? idle : value;
}
