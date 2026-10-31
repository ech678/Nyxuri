.pragma library

// Maps nyxuri's freedesktop-style weather icon names onto Material Symbols.
//
// end4-pC has an equivalent (modules/common/Icons.qml, getWeatherIcon) but its
// table is keyed by WWO codes while nyxuri's WeatherBackend emits WMO codes, so
// the table is not portable. Keying off the resolved icon name instead keeps
// the day/night distinction that the backend already made and avoids a second
// code table that could drift.
function symbolFor(iconName) {
    switch (String(iconName || "")) {
    case "weather-clear":
        return "clear_day";
    case "weather-clear-night":
        return "clear_night";
    case "weather-few-clouds":
        return "partly_cloudy_day";
    case "weather-few-clouds-night":
        return "partly_cloudy_night";
    case "weather-overcast":
        return "cloud";
    case "weather-fog":
        return "foggy";
    case "weather-showers-scattered":
        return "rainy_light";
    case "weather-rain":
        return "rainy";
    case "weather-snow":
        return "weather_snowy";
    case "weather-showers":
        return "rainy_heavy";
    case "weather-snow-scattered":
        return "snowing";
    case "weather-storm":
        return "thunderstorm";
    default:
        return "cloud";
    }
}
