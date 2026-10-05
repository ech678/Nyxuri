.pragma library

var units = {
    length: {
        base: "meter",
        aliases: {
            "millimeter": "mm", "millimeters": "mm", "centimeter": "cm", "centimeters": "cm",
            "meter": "m", "meters": "m", "metre": "m", "metres": "m",
            "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
            "inch": "in", "inches": "in", "foot": "ft", "feet": "ft",
            "yard": "yd", "yards": "yd", "mile": "mi", "miles": "mi",
            "nauticalmile": "nmi", "nauticalmiles": "nmi"
        },
        factors: {
            "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
            "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
            "m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1,
            "km": 1000, "kilometer": 1000, "kilometers": 1000, "kilometre": 1000, "kilometres": 1000,
            "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
            "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
            "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
            "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
            "nmi": 1852, "nauticalmile": 1852, "nauticalmiles": 1852
        },
        labels: {
            "mm": "mm", "cm": "cm", "m": "m", "km": "km", "in": "in", "ft": "ft",
            "yd": "yd", "mi": "mi", "nmi": "nmi"
        }
    },
    mass: {
        base: "gram",
        aliases: {
            "milligram": "mg", "milligrams": "mg", "gram": "g", "grams": "g",
            "kilogram": "kg", "kilograms": "kg", "tonne": "t", "tonnes": "t",
            "ounce": "oz", "ounces": "oz", "lbs": "lb", "pound": "lb", "pounds": "lb",
            "stone": "st", "stones": "st"
        },
        factors: {
            "mg": 0.001, "milligram": 0.001, "milligrams": 0.001,
            "g": 1, "gram": 1, "grams": 1,
            "kg": 1000, "kilogram": 1000, "kilograms": 1000,
            "t": 1000000, "tonne": 1000000, "tonnes": 1000000,
            "oz": 28.349523125, "ounce": 28.349523125, "ounces": 28.349523125,
            "lb": 453.59237, "lbs": 453.59237, "pound": 453.59237, "pounds": 453.59237,
            "st": 6350.29318, "stone": 6350.29318, "stones": 6350.29318
        },
        labels: {
            "mg": "mg", "g": "g", "kg": "kg", "t": "t", "oz": "oz", "lb": "lb", "st": "st"
        }
    },
    data: {
        base: "byte",
        aliases: {
            "byte": "b", "bytes": "b", "kilobyte": "kb", "kilobytes": "kb",
            "megabyte": "mb", "megabytes": "mb", "gigabyte": "gb", "gigabytes": "gb",
            "terabyte": "tb", "terabytes": "tb"
        },
        factors: {
            "b": 1, "byte": 1, "bytes": 1,
            "kb": 1000, "kilobyte": 1000, "kilobytes": 1000,
            "mb": 1000000, "megabyte": 1000000, "megabytes": 1000000,
            "gb": 1000000000, "gigabyte": 1000000000, "gigabytes": 1000000000,
            "tb": 1000000000000, "terabyte": 1000000000000, "terabytes": 1000000000000,
            "kib": 1024, "mib": 1048576, "gib": 1073741824, "tib": 1099511627776
        },
        labels: {
            "b": "B", "kb": "kB", "mb": "MB", "gb": "GB", "tb": "TB",
            "kib": "KiB", "mib": "MiB", "gib": "GiB", "tib": "TiB"
        }
    },
    speed: {
        base: "meterPerSecond",
        aliases: {
            "kph": "kmh", "m/s": "mps", "mi/h": "mph", "knots": "knot", "kn": "knot"
        },
        factors: {
            "mps": 1, "m/s": 1,
            "kmh": 0.2777777777777778, "km/h": 0.2777777777777778, "kph": 0.2777777777777778,
            "mph": 0.44704, "mi/h": 0.44704,
            "knot": 0.5144444444444445, "knots": 0.5144444444444445, "kn": 0.5144444444444445
        },
        labels: {
            "mps": "m/s", "kmh": "km/h", "mph": "mph", "knot": "kn"
        }
    },
    time: {
        base: "second",
        aliases: {
            "millisecond": "ms", "milliseconds": "ms", "sec": "s", "second": "s", "seconds": "s",
            "minute": "min", "minutes": "min", "hr": "h", "hour": "h", "hours": "h",
            "day": "d", "days": "d", "week": "wk", "weeks": "wk"
        },
        factors: {
            "ms": 0.001, "millisecond": 0.001, "milliseconds": 0.001,
            "s": 1, "sec": 1, "second": 1, "seconds": 1,
            "min": 60, "minute": 60, "minutes": 60,
            "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
            "d": 86400, "day": 86400, "days": 86400,
            "wk": 604800, "week": 604800, "weeks": 604800
        },
        labels: {
            "ms": "ms", "s": "s", "min": "min", "h": "h", "d": "d", "wk": "wk"
        }
    }
}

var temperatureAliases = {
    "c": "celsius", "celsius": "celsius", "°c": "celsius", "centigrade": "celsius",
    "f": "fahrenheit", "fahrenheit": "fahrenheit", "°f": "fahrenheit",
    "k": "kelvin", "kelvin": "kelvin"
}

var temperatureLabels = {
    "celsius": "°C",
    "fahrenheit": "°F",
    "kelvin": "K"
}

function normalize(value) {
    return String(value || "").trim().toLowerCase().replace(/\s+/g, "").replace(/\.$/, "");
}

function findUnit(category, token) {
    const key = normalize(token);
    if (!key)
        return "";
    if (category.factors[key] !== undefined)
        return key;
    const entries = Object.keys(category.factors);
    for (let index = 0; index < entries.length; ++index) {
        if (entries[index] === key)
            return entries[index];
    }
    return "";
}

function categoryFor(token) {
    const key = normalize(token);
    if (temperatureAliases[key])
        return "temperature";
    const names = ["length", "mass", "data", "speed", "time"];
    for (let index = 0; index < names.length; ++index) {
        if (findUnit(units[names[index]], key) !== "")
            return names[index];
    }
    return "";
}

function canonical(category, token) {
    const key = normalize(token);
    const aliases = category.aliases || {};
    return aliases[key] !== undefined ? aliases[key] : key;
}

function labelFor(categoryName, key) {
    if (categoryName === "temperature")
        return temperatureLabels[temperatureAliases[key]] || "";
    const category = units[categoryName];
    if (!category)
        return "";
    const unit = canonical(category, key);
    const resolved = findUnit(category, unit);
    if (resolved === "")
        return unit;
    const label = category.labels[resolved];
    return label || resolved;
}

function format(value, precision) {
    if (!isFinite(value))
        return "";
    const digits = precision === undefined ? 6 : precision;
    const magnitude = Math.abs(value);
    if (magnitude !== 0 && (magnitude >= 1e12 || magnitude <= 1e-6)) {
        const parts = value.toExponential(4).split("e");
        const mantissa = parts[0].replace(/0+$/, "").replace(/\.$/, "");
        const sign = parts[1].charAt(0) === "-" ? "-" : "+";
        const exponent = parts[1].replace(/^[+-]/, "").replace(/^0+(?=\d)/, "");
        return mantissa + "e" + sign + (exponent.length < 2 ? "0" + exponent : exponent);
    }
    const rounded = Number(value.toFixed(digits));
    let text = String(rounded);
    if (text.indexOf("e") >= 0)
        return text;
    if (text.indexOf(".") >= 0)
        text = text.replace(/0+$/, "").replace(/\.$/, "");
    return text;
}

function toCelsius(value, scale) {
    if (scale === "fahrenheit")
        return (value - 32) * 5 / 9;
    if (scale === "kelvin")
        return value - 273.15;
    return value;
}

function fromCelsius(value, scale) {
    if (scale === "fahrenheit")
        return value * 9 / 5 + 32;
    if (scale === "kelvin")
        return value + 273.15;
    return value;
}

function parse(text) {
    const source = String(text || "").trim();
    if (!source || source.length > 96)
        return null;
    const match = /^([+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d{1,3})?)\s*([A-Za-z°/][A-Za-z°/0-9]*)\s*(?:to|in|as|->|=>)\s*([A-Za-z°/][A-Za-z°/0-9]*)$/.exec(
        source);
    if (!match)
        return null;
    const amount = Number(match[1]);
    if (!isFinite(amount))
        return null;
    const fromCategory = categoryFor(match[2]);
    const toCategory = categoryFor(match[3]);
    if (!fromCategory || fromCategory !== toCategory)
        return null;
    if (fromCategory === "temperature")
        return {
            category: "temperature",
            amount: amount,
            from: temperatureAliases[normalize(match[2])],
            to: temperatureAliases[normalize(match[3])],
            fromLabel: labelFor("temperature", match[2]),
            toLabel: labelFor("temperature", match[3])
        };
    const category = units[fromCategory];
    const fromUnit = canonical(category, findUnit(category, match[2]));
    const toUnit = canonical(category, findUnit(category, match[3]));
    if (fromUnit === "" || toUnit === "")
        return null;
    return {
        category: fromCategory,
        amount: amount,
        from: fromUnit,
        to: toUnit,
        fromLabel: labelFor(fromCategory, fromUnit),
        toLabel: labelFor(fromCategory, toUnit)
    };
}

function convert(request) {
    if (!request)
        return "";
    if (request.category === "temperature")
        return format(fromCelsius(toCelsius(request.amount, request.from), request.to));
    const category = units[request.category];
    if (!category)
        return "";
    const fromFactor = category.factors[request.from];
    const toFactor = category.factors[request.to];
    if (fromFactor === undefined || toFactor === undefined || toFactor === 0)
        return "";
    return format(request.amount * fromFactor / toFactor);
}

function answer(text) {
    const request = parse(text);
    if (!request)
        return null;
    const value = convert(request);
    if (value === "")
        return null;
    return {
        input: request.amount,
        value: value,
        fromLabel: request.fromLabel,
        toLabel: request.toLabel,
        expression: format(request.amount) + " " + request.fromLabel + " = " + value + " " + request.toLabel,
        copyText: value
    };
}