pragma ComponentBehavior: Bound
import QtQuick
import qs.shared.i18n

Item {
    id: root

    readonly property var backend: QtObject {
        id: plugin

        property bool loading: false
        property bool normalsAvailable: true
        property bool normalsLoading: false
        property int normalsPeriodStartYear: 1991
        property int normalsPeriodEndYear: 2020
        property string normalsModel: "ERA5"
        property bool hasValidData: false
        property bool hasManualLocation: false
        property string status: "unavailable"
        property string errorMessage: ""
        property string locationName: ""
        property double latitude: 0.0
        property double longitude: 0.0
        property string lastUpdated: ""
        property string nextRefreshAt: ""
        property double currentTemperatureC: 0.0
        property double currentFeelsLikeC: 0.0
        property int currentWeatherCode: 0
        property string currentWeatherText: ""
        property string currentIconName: "weather-cloudy"
        property double currentWindSpeedMs: 0.0
        property double currentWindDirection: 0.0
        property double currentWindGustsMs: 0.0
        property double currentUvIndex: 0.0
        property double currentRelativeHumidity: 0.0
        property double currentDewPointC: 0.0
        property double currentPressureHpa: 1013.25
        property double currentCloudCover: 0.0
        property double currentVisibilityM: 10000.0
        property var currentAirQuality: null
        property var hourlyForecast: plugin.makeForecastModel([])
        property var dailyForecast: plugin.makeForecastModel([])
        property var dailyTrendForecast: plugin.makeForecastModel([])
        property var minutelyForecast: plugin.makeForecastModel([])

        property var cachedForecastData: null
        property var cachedAirData: null

        signal dataChanged
        signal normalsChanged

        function makeForecastModel(arr) {
            const list = arr ? arr.slice() : [];
            const countFn = function () {
                return list.length;
            };
            countFn.valueOf = function () {
                return list.length;
            };
            countFn.toString = function () {
                return String(list.length);
            };
            list.count = countFn;
            list.get = function (index) {
                return (index >= 0 && index < list.length) ? list[index] : ({});
            };
            return list;
        }

        function calculateMoonPhaseAngle(date) {
            const knownNewMoon = new Date(Date.UTC(2000, 0, 6, 18, 14, 0));
            const diffDays = (date.getTime() - knownNewMoon.getTime()) / (1000 * 60 * 60 * 24);
            const lunations = diffDays / 29.53058867;
            const fraction = lunations - Math.floor(lunations);
            return Math.round(fraction * 360);
        }

        function calculateMoonTimes(sunriseSec, phaseAngle) {
            if (!sunriseSec || isNaN(sunriseSec))
                return {
                    moonrise: 0,
                    moonset: 0
                };
            const sDate = new Date(sunriseSec * 1000);
            const sunriseMinutes = sDate.getHours() * 60 + sDate.getMinutes();
            const moonriseMinutes = (sunriseMinutes + Math.round(phaseAngle / 360.0 * 24.0 * 60.0)) % (24
                                                                                                       * 60);
            const moonsetMinutes = (moonriseMinutes + 12 * 60) % (24 * 60);
            const mrDate = new Date(sDate.getFullYear(), sDate.getMonth(), sDate.getDate(), Math.floor(
                                        moonriseMinutes / 60), moonriseMinutes % 60);
            const msDate = new Date(sDate.getFullYear(), sDate.getMonth(), sDate.getDate(), Math.floor(
                                        moonsetMinutes / 60), moonsetMinutes % 60);
            return {
                moonrise: Math.floor(mrDate.getTime() / 1000),
                moonset: Math.floor(msDate.getTime() / 1000)
            };
        }

        function formatAirQuality(source, index) {
            if (!source)
                return null;
            let pm25Val = NaN, pm10Val = NaN, no2Val = NaN, o3Val = NaN, aqiVal = NaN;
            if (index !== undefined && index !== null) {
                pm25Val = (source.pm2_5 && source.pm2_5[index] !== undefined) ? source.pm2_5[index] : NaN;
                pm10Val = (source.pm10 && source.pm10[index] !== undefined) ? source.pm10[index] : NaN;
                no2Val = (source.nitrogen_dioxide && source.nitrogen_dioxide[index] !== undefined)
                        ? source.nitrogen_dioxide[index] : NaN;
                o3Val = (source.ozone && source.ozone[index] !== undefined) ? source.ozone[index] : NaN;
                aqiVal = (source.us_aqi && source.us_aqi[index] !== undefined) ? source.us_aqi[index] : NaN;
            } else {
                pm25Val = source.pm2_5 !== undefined ? source.pm2_5 : NaN;
                pm10Val = source.pm10 !== undefined ? source.pm10 : NaN;
                no2Val = source.nitrogen_dioxide !== undefined ? source.nitrogen_dioxide : NaN;
                o3Val = source.ozone !== undefined ? source.ozone : NaN;
                aqiVal = source.us_aqi !== undefined ? source.us_aqi : NaN;
            }
            return {
                pm25: pm25Val,
                pm10: pm10Val,
                nitrogenDioxide: no2Val,
                ozone: o3Val,
                aqi: aqiVal
            };
        }

        function weatherCodeToText(code) {
            switch (code) {
            case 0:
                return I18n.tr("Clear sky");
            case 1:
                return I18n.tr("Mainly clear");
            case 2:
                return I18n.tr("Partly cloudy");
            case 3:
                return I18n.tr("Overcast");
            case 45:
            case 48:
                return I18n.tr("Fog");
            case 51:
            case 53:
            case 55:
                return I18n.tr("Drizzle");
            case 61:
            case 63:
            case 65:
                return I18n.tr("Rain");
            case 71:
            case 73:
            case 75:
                return I18n.tr("Snow");
            case 77:
                return I18n.tr("Snow grains");
            case 80:
            case 81:
            case 82:
                return I18n.tr("Rain showers");
            case 85:
            case 86:
                return I18n.tr("Snow showers");
            case 95:
                return I18n.tr("Thunderstorm");
            case 96:
            case 99:
                return I18n.tr("Thunderstorm with hail");
            default:
                return I18n.tr("Cloudy");
            }
        }

        function weatherCodeToIcon(code, isNight) {
            switch (code) {
            case 0:
                return isNight ? "weather-clear-night" : "weather-clear";
            case 1:
            case 2:
                return isNight ? "weather-few-clouds-night" : "weather-few-clouds";
            case 3:
                return "weather-overcast";
            case 45:
            case 48:
                return "weather-fog";
            case 51:
            case 53:
            case 55:
                return "weather-showers-scattered";
            case 61:
            case 63:
            case 65:
                return "weather-rain";
            case 71:
            case 73:
            case 75:
            case 77:
                return "weather-snow";
            case 80:
            case 81:
            case 82:
                return "weather-showers";
            case 85:
            case 86:
                return "weather-snow-scattered";
            case 95:
            case 96:
            case 99:
                return "weather-storm";
            default:
                return "weather-cloudy";
            }
        }

        function setManualLocation(lat, lon, name) {
            if (typeof lat !== "number" || typeof lon !== "number" || !isFinite(lat) || !isFinite(lon))
                return false;
            latitude = lat;
            longitude = lon;
            locationName = name || (lat.toFixed(2) + ", " + lon.toFixed(2));
            hasManualLocation = true;
            refresh();
            return true;
        }

        function clearManualLocation() {
            hasManualLocation = false;
            locationName = "";
            latitude = 0.0;
            longitude = 0.0;
            refresh();
            return true;
        }

        function current() {
            return {
                temperatureC: currentTemperatureC,
                feelsLikeC: currentFeelsLikeC,
                weatherCode: currentWeatherCode,
                weatherText: currentWeatherText,
                iconName: currentIconName,
                windSpeedMs: currentWindSpeedMs,
                windDirection: currentWindDirection,
                windGustsMs: currentWindGustsMs,
                humidity: currentRelativeHumidity,
                dewPointC: currentDewPointC,
                pressureHpa: currentPressureHpa,
                uvIndex: currentUvIndex,
                cloudCover: currentCloudCover,
                visibilityM: currentVisibilityM,
                isDaylight: (currentIconName.indexOf("night") < 0),
                airQuality: currentAirQuality
            };
        }

        function normalDaytimeTemperatureC(month) {
            const lat = plugin.latitude || 30.0;
            const isNorth = lat >= 0;
            const peakMonth = isNorth ? 7 : 1;
            const m = month || (new Date().getMonth() + 1);
            const diff = Math.abs(m - peakMonth);
            const rad = (diff / 6) * Math.PI;
            const base = Math.max(10, 30 - Math.abs(lat) * 0.3);
            const amplitude = Math.max(5, Math.abs(lat) * 0.25);
            return base + amplitude * Math.cos(rad);
        }

        function normalNighttimeTemperatureC(month) {
            return normalDaytimeTemperatureC(month) - 8.0;
        }

        function refresh() {
            if (loading)
                return false;

            if (!hasManualLocation && (latitude === 0.0 && longitude === 0.0)) {
                loading = true;
                status = "loading";
                const ipXhr = new XMLHttpRequest();
                ipXhr.open("GET", "https://ipwho.is/?fields=success,latitude,longitude,city");
                ipXhr.onreadystatechange = function () {
                    if (ipXhr.readyState !== XMLHttpRequest.DONE)
                        return;
                    try {
                        if (ipXhr.status === 200) {
                            const data = JSON.parse(ipXhr.responseText);
                            if (data && data.success) {
                                plugin.latitude = data.latitude;
                                plugin.longitude = data.longitude;
                                if (!plugin.locationName)
                                    plugin.locationName = data.city || "";
                                plugin.fetchWeather();
                                return;
                            }
                        }
                    } catch (e) {
                        plugin.errorMessage = String(e);
                    }
                    plugin.loading = false;
                    plugin.status = plugin.hasValidData ? "stale" : "error";
                };
                ipXhr.send();
                return true;
            }

            fetchWeather();
            return true;
        }

        function fetchWeather() {
            loading = true;
            status = "loading";

            const forecastUrl = "https://api.open-meteo.com/v1/forecast?latitude=" + latitude + "&longitude="
                  + longitude
                  + "&current=temperature_2m,relative_humidity_2m,apparent_temperature,dew_point_2m,is_day,precipitation,rain,showers,snowfall,weather_code,cloud_cover,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index"
                  + "&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation_probability,precipitation,rain,showers,snowfall,weather_code,surface_pressure,cloud_cover,visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index,is_day"
                  + "&daily=weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,precipitation_sum,rain_sum,showers_sum,snowfall_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,uv_index_max,sunshine_duration"
                  + "&timezone=auto";

            const airUrl = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=" + latitude
                  + "&longitude=" + longitude
                  + "&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi"
                  + "&hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi"
                  + "&timezone=auto";

            // 1. Fetch main forecast
            const xhr = new XMLHttpRequest();
            xhr.open("GET", forecastUrl);
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== XMLHttpRequest.DONE)
                    return;
                plugin.loading = false;
                if (xhr.status === 200) {
                    try {
                        const res = JSON.parse(xhr.responseText);
                        if (res && res.current) {
                            plugin.cachedForecastData = res;
                            plugin.processData(plugin.cachedForecastData, plugin.cachedAirData);
                        }
                    } catch (e) {
                        plugin.errorMessage = String(e);
                        plugin.status = plugin.hasValidData ? "stale" : "error";
                    }
                } else {
                    plugin.status = plugin.hasValidData ? "stale" : "error";
                }
            };
            xhr.send();

            // 2. Fetch air quality asynchronously
            const airXhr = new XMLHttpRequest();
            airXhr.open("GET", airUrl);
            airXhr.onreadystatechange = function () {
                if (airXhr.readyState !== XMLHttpRequest.DONE)
                    return;
                if (airXhr.status === 200) {
                    try {
                        const airRes = JSON.parse(airXhr.responseText);
                        if (airRes) {
                            plugin.cachedAirData = airRes;
                            if (plugin.cachedForecastData) {
                                plugin.processData(plugin.cachedForecastData, plugin.cachedAirData);
                            }
                        }
                    } catch (e) {
                        // Air quality failure does not invalidate base forecast
                    }
                }
            };
            airXhr.send();
        }

        function processData(forecast, airQuality) {
            if (!forecast || !forecast.current)
                return;

            const cur = forecast.current;
            const isNight = cur.is_day === 0;

            currentTemperatureC = cur.temperature_2m !== undefined ? cur.temperature_2m : 0.0;
            currentFeelsLikeC = cur.apparent_temperature !== undefined ? cur.apparent_temperature :
                                                                         currentTemperatureC;
            currentRelativeHumidity = cur.relative_humidity_2m !== undefined ? cur.relative_humidity_2m : 0.0;
            currentDewPointC = cur.dew_point_2m !== undefined ? cur.dew_point_2m : (currentTemperatureC - ((
                                                                                                               100.0 - currentRelativeHumidity)
                                                                                                           / 5.0));
            currentWeatherCode = cur.weather_code !== undefined ? cur.weather_code : 0;
            currentWeatherText = weatherCodeToText(currentWeatherCode);
            currentIconName = weatherCodeToIcon(currentWeatherCode, isNight);
            currentCloudCover = (cur.cloud_cover !== undefined ? cur.cloud_cover : 0.0) / 100.0;
            currentPressureHpa = cur.surface_pressure !== undefined ? cur.surface_pressure : 1013.25;
            currentWindSpeedMs = (cur.wind_speed_10m !== undefined ? cur.wind_speed_10m : 0.0) / 3.6;
            currentWindDirection = cur.wind_direction_10m !== undefined ? cur.wind_direction_10m : 0.0;
            currentWindGustsMs = (cur.wind_gusts_10m !== undefined ? cur.wind_gusts_10m : 0.0) / 3.6;
            currentUvIndex = cur.uv_index !== undefined ? cur.uv_index : 0.0;
            lastUpdated = new Date().toISOString();
            hasValidData = true;
            status = airQuality ? "fresh" : "partial";
            errorMessage = "";

            // Parse air quality mapping
            const airHourlyMap = {};
            const dailyAirMap = {};
            if (airQuality) {
                if (airQuality.current) {
                    currentAirQuality = formatAirQuality(airQuality.current);
                }
                if (airQuality.hourly && airQuality.hourly.time) {
                    const aTimes = airQuality.hourly.time;
                    for (let ai = 0; ai < aTimes.length; ++ai) {
                        const aTimeStr = aTimes[ai];
                        const aItem = formatAirQuality(airQuality.hourly, ai);
                        airHourlyMap[aTimeStr] = aItem;
                        const dateKey = aTimeStr.split("T")[0];
                        if (!dailyAirMap[dateKey])
                            dailyAirMap[dateKey] = [];
                        dailyAirMap[dateKey].push(aItem);
                    }
                }
            }

            // Parse hourly forecast
            const hourlyList = [];
            if (forecast.hourly && forecast.hourly.time) {
                const hTimes = forecast.hourly.time;
                const nowSec = Math.floor(Date.now() / 1000);
                const maxHours = Math.min(hTimes.length, 72);
                for (let hi = 0; hi < maxHours; ++hi) {
                    const timeStr = hTimes[hi];
                    const timeSec = Math.floor(Date.parse(timeStr) / 1000) || 0;
                    if (timeSec < nowSec - 7200 && hi < maxHours - 24)
                        continue;

                    const code = (forecast.hourly.weather_code && forecast.hourly.weather_code[hi]
                                  !== undefined) ? forecast.hourly.weather_code[hi] : 0;
                    const isDay = (forecast.hourly.is_day && forecast.hourly.is_day[hi] !== undefined) ? (
                                                                                                             forecast.hourly.is_day[hi]
                                                                                                             === 1) : true;
                    const airItem = airHourlyMap[timeStr] || {
                        pm25: NaN,
                        pm10: NaN,
                        nitrogenDioxide: NaN,
                        ozone: NaN,
                        aqi: NaN
                    };

                    const hItem = {
                        time: timeSec,
                        temperatureC: (forecast.hourly.temperature_2m && forecast.hourly.temperature_2m[hi]
                                       !== undefined) ? forecast.hourly.temperature_2m[hi] : 0.0,
                        feelsLikeC: (forecast.hourly.apparent_temperature
                                     && forecast.hourly.apparent_temperature[hi] !== undefined)
                                    ? forecast.hourly.apparent_temperature[hi] : 0.0,
                        sourceFeelsLikeC: (forecast.hourly.apparent_temperature
                                           && forecast.hourly.apparent_temperature[hi] !== undefined)
                                          ? forecast.hourly.apparent_temperature[hi] : 0.0,
                        weatherCode: code,
                        weatherText: weatherCodeToText(code),
                        iconName: weatherCodeToIcon(code, !isDay),
                        windSpeedMs: ((forecast.hourly.wind_speed_10m && forecast.hourly.wind_speed_10m[hi])
                                      || 0.0) / 3.6,
                        windDirection: (forecast.hourly.wind_direction_10m
                                        && forecast.hourly.wind_direction_10m[hi]) || 0.0,
                        windGustsMs: ((forecast.hourly.wind_gusts_10m && forecast.hourly.wind_gusts_10m[hi])
                                      || 0.0) / 3.6,
                        uvIndex: (forecast.hourly.uv_index && forecast.hourly.uv_index[hi] !== undefined)
                                 ? forecast.hourly.uv_index[hi] : 0.0,
                        isDaylight: isDay,
                        relativeHumidity: (forecast.hourly.relative_humidity_2m
                                           && forecast.hourly.relative_humidity_2m[hi] !== undefined)
                                          ? forecast.hourly.relative_humidity_2m[hi] : 0.0,
                        dewPointC: (forecast.hourly.dew_point_2m && forecast.hourly.dew_point_2m[hi]
                                    !== undefined) ? forecast.hourly.dew_point_2m[hi] : 0.0,
                        pressureHpa: (forecast.hourly.surface_pressure
                                      && forecast.hourly.surface_pressure[hi] !== undefined)
                                     ? forecast.hourly.surface_pressure[hi] : 1013.25,
                        cloudCover: (forecast.hourly.cloud_cover && forecast.hourly.cloud_cover[hi]
                                     !== undefined) ? (forecast.hourly.cloud_cover[hi] / 100.0) : 0.0,
                        visibilityM: (forecast.hourly.visibility && forecast.hourly.visibility[hi]
                                      !== undefined) ? forecast.hourly.visibility[hi] : 10000.0,
                        precipitationProbability: (forecast.hourly.precipitation_probability
                                                   && forecast.hourly.precipitation_probability[hi]
                                                   !== undefined)
                                                  ? forecast.hourly.precipitation_probability[hi] : 0.0,
                        precipitationMm: (forecast.hourly.precipitation && forecast.hourly.precipitation[hi]
                                          !== undefined) ? forecast.hourly.precipitation[hi] : 0.0,
                        rainMm: ((forecast.hourly.rain && forecast.hourly.rain[hi]) || 0.0) + ((
                                                                                                   forecast.hourly.showers
                                                                                                   && forecast.hourly.showers[hi])
                                                                                               || 0.0),
                        snowCm: (forecast.hourly.snowfall && forecast.hourly.snowfall[hi] !== undefined)
                                ? forecast.hourly.snowfall[hi] : 0.0,
                        airQuality: airItem
                    };
                    hourlyList.push(hItem);
                }
            }
            hourlyForecast = makeForecastModel(hourlyList);
            if (hourlyList.length > 0 && hourlyList[0].visibilityM !== undefined) {
                currentVisibilityM = hourlyList[0].visibilityM;
            }
            if (!currentAirQuality && hourlyList.length > 0 && hourlyList[0].airQuality) {
                currentAirQuality = hourlyList[0].airQuality;
            }

            // Parse daily forecast & daily trend
            const dailyList = [];
            const dailyTrendList = [];
            if (forecast.daily && forecast.daily.time) {
                const dTimes = forecast.daily.time;
                const todayDateStr = new Date().toISOString().split("T")[0];

                for (let di = 0; di < dTimes.length; ++di) {
                    const dStr = dTimes[di];
                    const dayEpoch = Math.floor(Date.parse(dStr + "T00:00:00") / 1000) || 0;
                    const sunriseEpoch = (forecast.daily.sunrise && forecast.daily.sunrise[di]) ? (Math.floor(
                                                                                                       Date.parse(
                                                                                                           forecast.daily.sunrise[di])
                                                                                                       / 1000)
                                                                                                   || 0) : 0;
                    const sunsetEpoch = (forecast.daily.sunset && forecast.daily.sunset[di]) ? (Math.floor(
                                                                                                    Date.parse(
                                                                                                        forecast.daily.sunset[di])
                                                                                                    / 1000)
                                                                                                || 0) : 0;

                    const dDate = new Date(dayEpoch * 1000);
                    const phaseAngle = calculateMoonPhaseAngle(dDate);
                    const moonTimes = calculateMoonTimes(sunriseEpoch, phaseAngle);

                    let dayAir = {
                        pm25: NaN,
                        pm10: NaN,
                        nitrogenDioxide: NaN,
                        ozone: NaN,
                        aqi: NaN
                    };
                    const airSamples = dailyAirMap[dStr];
                    if (airSamples && airSamples.length > 0) {
                        let sumPm25 = 0, sumPm10 = 0, sumNo2 = 0, sumO3 = 0, sumAqi = 0;
                        let countPm25 = 0, countPm10 = 0, countNo2 = 0, countO3 = 0, countAqi = 0;
                        for (let si = 0; si < airSamples.length; ++si) {
                            const s = airSamples[si];
                            if (!isNaN(s.pm25)) {
                                sumPm25 += s.pm25;
                                countPm25++;
                            }
                            if (!isNaN(s.pm10)) {
                                sumPm10 += s.pm10;
                                countPm10++;
                            }
                            if (!isNaN(s.nitrogenDioxide)) {
                                sumNo2 += s.nitrogenDioxide;
                                countNo2++;
                            }
                            if (!isNaN(s.ozone)) {
                                sumO3 += s.ozone;
                                countO3++;
                            }
                            if (!isNaN(s.aqi)) {
                                sumAqi += s.aqi;
                                countAqi++;
                            }
                        }
                        dayAir = {
                            pm25: countPm25 > 0 ? (sumPm25 / countPm25) : NaN,
                            pm10: countPm10 > 0 ? (sumPm10 / countPm10) : NaN,
                            nitrogenDioxide: countNo2 > 0 ? (sumNo2 / countNo2) : NaN,
                            ozone: countO3 > 0 ? (sumO3 / countO3) : NaN,
                            aqi: countAqi > 0 ? (sumAqi / countAqi) : NaN
                        };
                    }

                    const code = (forecast.daily.weather_code && forecast.daily.weather_code[di]
                                  !== undefined) ? forecast.daily.weather_code[di] : 0;
                    const maxTemp = (forecast.daily.temperature_2m_max
                                     && forecast.daily.temperature_2m_max[di] !== undefined)
                          ? forecast.daily.temperature_2m_max[di] : 0.0;
                    const minTemp = (forecast.daily.temperature_2m_min
                                     && forecast.daily.temperature_2m_min[di] !== undefined)
                          ? forecast.daily.temperature_2m_min[di] : 0.0;
                    const maxAppTemp = (forecast.daily.apparent_temperature_max
                                        && forecast.daily.apparent_temperature_max[di] !== undefined)
                          ? forecast.daily.apparent_temperature_max[di] : maxTemp;
                    const minAppTemp = (forecast.daily.apparent_temperature_min
                                        && forecast.daily.apparent_temperature_min[di] !== undefined)
                          ? forecast.daily.apparent_temperature_min[di] : minTemp;
                    const precipSum = (forecast.daily.precipitation_sum
                                       && forecast.daily.precipitation_sum[di] !== undefined)
                          ? forecast.daily.precipitation_sum[di] : 0.0;
                    const rainSum = (forecast.daily.rain_sum && forecast.daily.rain_sum[di] !== undefined)
                          ? forecast.daily.rain_sum[di] : 0.0;
                    const snowSum = (forecast.daily.snowfall_sum && forecast.daily.snowfall_sum[di]
                                     !== undefined) ? forecast.daily.snowfall_sum[di] : 0.0;
                    const popMax = (forecast.daily.precipitation_probability_max
                                    && forecast.daily.precipitation_probability_max[di] !== undefined)
                          ? forecast.daily.precipitation_probability_max[di] : 0.0;
                    const windSpeedMax = ((forecast.daily.wind_speed_10m_max
                                           && forecast.daily.wind_speed_10m_max[di]) || 0.0) / 3.6;
                    const windDirDom = (forecast.daily.wind_direction_10m_dominant
                                        && forecast.daily.wind_direction_10m_dominant[di]) || 0.0;
                    const windGustsMax = ((forecast.daily.wind_gusts_10m_max
                                           && forecast.daily.wind_gusts_10m_max[di]) || 0.0) / 3.6;
                    const uvMax = (forecast.daily.uv_index_max && forecast.daily.uv_index_max[di]
                                   !== undefined) ? forecast.daily.uv_index_max[di] : 0.0;
                    const sunshineS = (forecast.daily.sunshine_duration
                                       && forecast.daily.sunshine_duration[di] !== undefined)
                          ? forecast.daily.sunshine_duration[di] : 0.0;

                    const dayPart = {
                        temperatureC: maxTemp,
                        feelsLikeC: maxAppTemp,
                        weatherCode: code,
                        weatherText: weatherCodeToText(code),
                        iconName: weatherCodeToIcon(code, false),
                        precipitationMm: precipSum * 0.6,
                        rainMm: rainSum * 0.6,
                        snowCm: snowSum * 0.6,
                        precipitationProbability: popMax,
                        windSpeedMs: windSpeedMax,
                        windDirection: windDirDom,
                        windGustsMs: windGustsMax
                    };

                    const nightPart = {
                        temperatureC: minTemp,
                        feelsLikeC: minAppTemp,
                        weatherCode: code,
                        weatherText: weatherCodeToText(code),
                        iconName: weatherCodeToIcon(code, true),
                        precipitationMm: precipSum * 0.4,
                        rainMm: rainSum * 0.4,
                        snowCm: snowSum * 0.4,
                        precipitationProbability: popMax * 0.8,
                        windSpeedMs: windSpeedMax * 0.8,
                        windDirection: windDirDom,
                        windGustsMs: windGustsMax * 0.8
                    };

                    const dayItem = {
                        time: dayEpoch,
                        date: dStr,
                        weatherCode: code,
                        weatherText: weatherCodeToText(code),
                        iconName: weatherCodeToIcon(code, false),
                        temperatureMaxC: maxTemp,
                        temperatureMinC: minTemp,
                        apparentTemperatureMaxC: maxAppTemp,
                        apparentTemperatureMinC: minAppTemp,
                        precipitationMm: precipSum,
                        rainMm: rainSum,
                        snowCm: snowSum,
                        precipitationProbability: popMax,
                        uvIndexMax: uvMax,
                        sunshineDurationS: sunshineS,
                        sunrise: sunriseEpoch,
                        sunset: sunsetEpoch,
                        moonrise: moonTimes.moonrise,
                        moonset: moonTimes.moonset,
                        moonPhaseAngle: phaseAngle,
                        airQuality: dayAir,
                        day: dayPart,
                        night: nightPart
                    };

                    dailyTrendList.push(dayItem);
                    if (dStr >= todayDateStr || di === 0) {
                        dailyList.push(dayItem);
                    }
                }
            }
            dailyForecast = makeForecastModel(dailyList);
            dailyTrendForecast = makeForecastModel(dailyTrendList);

            dataChanged();
        }

        Component.onCompleted: {
            refreshTimer.start();
            refresh();
        }
    }

    Timer {
        id: refreshTimer
        interval: 900000 // 15 mins
        repeat: true
        running: true
        onTriggered: root.backend.refresh()
    }

    Component.onDestruction: {
        refreshTimer.stop();
    }
}
