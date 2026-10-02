// Decimal-string arithmetic: no binary floating point or network on amount edits.
function trim(value) { return value.replace(/^0+(?=\d)/, ''); }
function decimal(value) {
    if (typeof value !== 'string' || value.length > 128) return null;
    const match = /^([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d{1,3}))?$/.exec(value);
    if (!match) return null;
    const pieces = match[2].split('.');
    const exponent = Number(match[3] || 0);
    if (Math.abs(exponent) > 128) return null;
    let digits = trim(pieces.join(''));
    let scale = (pieces[1] || '').length - exponent;
    if (scale < 0) { digits += '0'.repeat(-scale); scale = 0; }
    return {digits: trim(digits), scale: scale, negative: match[1] === '-'};
}
function format(digits, scale, negative) {
    digits = trim(digits).padStart(scale + 1, '0');
    let result = scale ? digits.slice(0, -scale) + '.' + digits.slice(-scale) : digits;
    if (scale) result = result.replace(/0+$/, '').replace(/\.$/, '');
    return (negative && /[1-9]/.test(result) ? '-' : '') + result;
}
function multiply(a, b) {
    const digits = Array(a.length + b.length).fill(0);
    for (let i = a.length - 1; i >= 0; --i)
        for (let j = b.length - 1; j >= 0; --j) digits[i + j + 1] += Number(a[i]) * Number(b[j]);
    for (let i = digits.length - 1; i > 0; --i) {
        digits[i - 1] += Math.floor(digits[i] / 10); digits[i] %= 10;
    }
    return trim(digits.join(''));
}
function compare(a, b) { return a.length !== b.length ? a.length - b.length : a === b ? 0 : a > b ? 1 : -1; }
function subtract(a, b) {
    let carry = 0, result = '';
    b = b.padStart(a.length, '0');
    for (let i = a.length - 1; i >= 0; --i) {
        let digit = Number(a[i]) - Number(b[i]) - carry;
        carry = digit < 0 ? 1 : 0;
        result = String(digit + carry * 10) + result;
    }
    return trim(result);
}
function divide(a, b) {
    let remainder = '0', quotient = '';
    for (const digit of a) {
        remainder = trim(remainder + digit);
        let count = 0;
        while (compare(remainder, b) >= 0) { remainder = subtract(remainder, b); count++; }
        quotient += String(count);
    }
    return {digits: trim(quotient), remainder: remainder};
}
function convert(amount, rate, reverse) {
    const a = decimal(amount), r = decimal(rate);
    if (!a || !r || r.negative || r.digits === '0') return '';
    if (!reverse) return format(multiply(a.digits, r.digits), a.scale + r.scale, a.negative);
    // Reverse conversion is rounded half-even to 24 decimal places.
    const places = 24;
    const divided = divide(a.digits + '0'.repeat(r.scale + places), r.digits + '0'.repeat(a.scale));
    const denominator = r.digits + '0'.repeat(a.scale);
    const halfway = compare(multiply(divided.remainder, '2'), denominator);
    let digits = divided.digits;
    if (halfway > 0 || (halfway === 0 && Number(digits.slice(-1)) % 2)) {
        let carry = 1, output = '';
        for (let i = digits.length - 1; i >= 0; --i) {
            const value = Number(digits[i]) + carry;
            output = String(value % 10) + output; carry = Math.floor(value / 10);
        }
        digits = (carry ? '1' : '') + output;
    }
    return format(digits, places, a.negative);
}
function candidates(catalog, query) {
    const needle = query.trim().toLowerCase();
    function rank(item) {
        const code = item.text.toLowerCase(), name = item.name.toLowerCase();
        return !needle || code === needle ? 0 : code.startsWith(needle) ? 1 : name.startsWith(needle) ? 2 : (code + ' ' + name).includes(needle) ? 3 : 4;
    }
    return catalog.filter(item => rank(item) < 4).slice().sort((a, b) => rank(a) - rank(b) || a.text.localeCompare(b.text));
}
function seed(text) {
    const match = /^([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s+([A-Z]{3})\s+to\s+([A-Z]{3})$/i.exec(text.trim());
    return {amount: match ? match[1] : '1', from: match ? match[2].toUpperCase() : 'USD', to: match ? match[3].toUpperCase() : 'EUR'};
}
