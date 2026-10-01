function timeExpression(text, source, target) {
    if (!target || !text.trim()) return '';
    let value = text.trim();
    if (/^\d{1,2}$/.test(value)) value = value.padStart(2, '0') + ':00';
    else if (/^\d{3,4}$/.test(value)) value = value.padStart(4, '0').replace(/(\d{2})(\d{2})/, '$1:$2');
    return value + (source ? ' ' + source : '') + ' to ' + target;
}

// Keep the date on derived values so editing across midnight preserves the day.
function editableTime(datetime) {
    const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/.exec(String(datetime || ''));
    return match ? match[1] + ' ' + match[2] : '';
}
