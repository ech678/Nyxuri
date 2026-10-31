function current(request, generation, instance) {
    return !!request && request.generation === generation && request.instance === instance;
}

function copyable(value, request, active, state, generation, instance) {
    return active && state === "valid" && current(request, generation, instance)
        && !!value && value.ok === true && value.error === null
        && typeof value.answer === "string" && value.answer.length > 0;
}
