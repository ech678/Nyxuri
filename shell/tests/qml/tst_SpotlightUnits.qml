import QtQuick
import QtTest
import "../../modules/launcher/SpotlightUnits.js" as Units

TestCase {
    name: "SpotlightUnits"

    function test_length_conversion_is_exact() {
        const result = Units.answer("5 km to miles");
        verify(result !== null);
        compare(result.copyText, "3.106856");
        compare(result.fromLabel, "km");
        compare(result.toLabel, "mi");
    }

    function test_metric_prefixes_round_trip() {
        compare(Units.answer("1500 m to km").copyText, "1.5");
        compare(Units.answer("2.5 cm to mm").copyText, "25");
        compare(Units.answer("1 mi to km").copyText, "1.609344");
    }

    function test_mass_uses_international_pound() {
        compare(Units.answer("1 lb to g").copyText, "453.59237");
        compare(Units.answer("16 oz to lb").copyText, "1");
        compare(Units.answer("1 kg to lb").copyText, "2.204623");
    }

    function test_temperature_offsets_are_handled() {
        compare(Units.answer("100 F to C").copyText, "37.777778");
        compare(Units.answer("0 C to F").copyText, "32");
        compare(Units.answer("0 C to K").copyText, "273.15");
        compare(Units.answer("32 F to K").copyText, "273.15");
        compare(Units.answer("-40 C to F").copyText, "-40");
    }

    function test_data_uses_decimal_and_binary_units() {
        compare(Units.answer("1 GB to MB").copyText, "1000");
        compare(Units.answer("1 GiB to MiB").copyText, "1024");
        compare(Units.answer("1 MiB to kB").copyText, "1048.576");
    }

    function test_speed_and_time_categories() {
        compare(Units.answer("100 km/h to mph").copyText, "62.137119");
        compare(Units.answer("1 knot to km/h").copyText, "1.852");
        compare(Units.answer("2 h to min").copyText, "120");
        compare(Units.answer("1 d to h").copyText, "24");
    }

    function test_aliases_and_separators_are_accepted() {
        verify(Units.answer("5 kilometres to miles") !== null);
        compare(Units.answer("5 km in miles").copyText, "3.106856");
        compare(Units.answer("5 km -> miles").copyText, "3.106856");
        compare(Units.answer("5 km => miles").copyText, "3.106856");
        compare(Units.answer("3 m as cm").copyText, "300");
    }

    function test_expression_is_readable() {
        compare(Units.answer("5 km to miles").expression, "5 km = 3.106856 mi");
        compare(Units.answer("100 f to c").expression, "100 °F = 37.777778 °C");
    }

    function test_cross_category_and_malformed_input_are_rejected() {
        compare(Units.answer("5 km to kg"), null);
        compare(Units.answer("5 km to celsius"), null);
        compare(Units.answer("km to miles"), null);
        compare(Units.answer("5 to 6"), null);
        compare(Units.answer("5 km to"), null);
        compare(Units.answer(""), null);
        compare(Units.answer("5 furlongs to meters"), null);
    }

    function test_extreme_magnitudes_use_exponential() {
        const tiny = Units.answer("1 mm to km");
        compare(tiny.copyText, "1e-06");
        const huge = Units.answer("1 tb to b");
        compare(huge.copyText, "1e+12");
    }
}
