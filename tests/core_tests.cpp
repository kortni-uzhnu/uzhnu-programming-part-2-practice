#include "../src/merge_sort.hpp"
#include "../src/character_frequency.hpp"
#include <algorithm>
#include <chrono>
#include <functional>
#include <random>

int checks = 0;
void check(bool condition, const std::string& name) {
    if (!condition) throw std::runtime_error("FAILED: " + name);
    ++checks;
}
void rejects(const std::function<void()>& action) {
    try { action(); }
    catch (const std::exception&) { ++checks; return; }
    throw std::runtime_error("FAILED: invalid input was accepted.");
}

void sortingChecks(const std::filesystem::path& folder) {
    for (const auto& value : {"0", "1", "1000000", "00012"})
        check(sorting::parseCount(value) <= sorting::maxElements, "Valid count");
    for (const auto& value : {"", "-1", "+1", "1.5", "10x", "1000001", "999999999999999999999"})
        rejects([&] { sorting::parseCount(value); });
    for (const auto& value : {"0", "-2.5", "+3.125", "2e5", "1.7976931348623157e308", "4.9406564584124654e-324"})
        check(std::isfinite(sorting::parseReal(value)), "Finite real parsing");
    for (const auto& value : {"", " ", "nan", "inf", "-inf", "1e999", "1e-999", "5x", "2,5", "0x12"})
        rejects([&] { sorting::parseReal(value); });
    std::mt19937 generator(12345);
    for (std::size_t count = 0; count < 400; ++count) {
        std::vector<double> values(count);
        for (double& value : values) value = (static_cast<int>(generator() % 1001) - 500) / 8.0;
        auto expected = values;
        std::stable_sort(expected.begin(), expected.end());
        sorting::Metrics metrics;
        sorting::mergeSort(values, &metrics);
        check(values == expected, "Merge sort agrees with independent standard-library oracle");
        auto bound = count < 2 ? 0 : static_cast<std::uint64_t>(count * std::ceil(std::log2(count)));
        check(metrics.comparisons <= bound, "Comparison-count bound");
    }
    std::vector<double> pair = {2, 1};
    sorting::Metrics metrics;
    sorting::mergeSort(pair, &metrics);
    check(metrics.comparisons == 1 && metrics.writes == 4, "Small exact operation counts");
    std::vector<double> zeroes = {0.0, -0.0, 0.0, -0.0};
    sorting::mergeSort(zeroes);
    check(!std::signbit(zeroes[0]) && std::signbit(zeroes[1]) &&
          !std::signbit(zeroes[2]) && std::signbit(zeroes[3]), "Equal-value stability with signed zero");
    for (double invalid : {std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()}) {
        std::vector<double> values = {1, invalid};
        rejects([&] { sorting::mergeSort(values); });
    }
    auto path = folder / "round trip.txt";
    std::vector<double> precise = {std::numeric_limits<double>::max(), std::numeric_limits<double>::lowest(),
        std::numeric_limits<double>::denorm_min(), -0.0, 100.0 / 3.0, 1e-300};
    practice::writeText(path, sorting::arrayText(precise));
    auto loaded = sorting::loadArray(path);
    check(loaded == precise && std::signbit(loaded[3]), "Exact floating-point round trip");
    for (const auto& text : {"", "-1\n", "2\n1\n", "1\n2\nextra", "1\nnan\n", "0\n1\n", "1\n2x\n"}) {
        practice::writeText(path, text);
        rejects([&] { sorting::loadArray(path); });
    }
    practice::writeText(path, "3\r\n3.5 -2 0\r\n");
    check(sorting::loadArray(path) == std::vector<double>({3.5, -2, 0}), "CRLF array input");
    practice::writeText(path, "0\n");
    check(sorting::loadArray(path).empty(), "Empty array file");
}

void characterChecks(const std::filesystem::path& folder) {
    auto frequencies = characters::countCharacters("Aa a!\t!");
    check(frequencies.at(U'A') == 1 && frequencies.at(U'a') == 2, "Case-sensitive counting");
    check(frequencies.at(U' ') == 1 && frequencies.at(U'!') == 2 && frequencies.at(U'\t') == 1,
          "Spaces, punctuation and tabs are counted");
    auto ukrainian = characters::countCharacters(u8"їЇї Привіт");
    check(ukrainian.at(U'ї') == 2 && ukrainian.at(U'Ї') == 1, "Ukrainian character counts");
    auto emoji = characters::countCharacters(u8"😀😀🙂");
    check(emoji.size() == 2 && emoji.at(U'😀') == 2, "Four-byte UTF-8 code points");
    auto combining = characters::countCharacters(u8"ée\u0301");
    check(combining.size() == 3 && combining.at(U'\u0301') == 1, "Code points are not grapheme clusters");
    const std::vector<char32_t> boundaries = {0, 0x7F, 0x80, 0x7FF, 0x800, 0xD7FF, 0xE000,
                                             0xFFFF, 0x10000, 0x10FFFF};
    for (auto code : boundaries) {
        auto result = characters::countCharacters(characters::utf8(code));
        check(result.size() == 1 && result.at(code) == 1, "UTF-8 boundary decoding");
    }
    std::mt19937 generator(9876);
    for (int repeat = 0; repeat < 100; ++repeat) {
        std::string text;
        characters::Frequencies expected;
        for (int j = 0; j < 100; ++j) {
            auto code = boundaries[generator() % boundaries.size()];
            text += characters::utf8(code); ++expected[code];
        }
        check(characters::countCharacters(text) == expected, "Random valid Unicode sequences");
    }
    const std::vector<std::string> malformed = {
        "", "\x80", "\xC0\xAF", "\xC1\xBF", "\xC2", "\xE2\x82", "\xF0\x9F\x98",
        "\xC2\x41", "\xE0\x80\x80", "\xED\xA0\x80", "\xF0\x80\x80\x80",
        "\xF4\x90\x80\x80", "\xF5\x80\x80\x80", "\xFE", "\xFF"
    };
    for (const auto& text : malformed) rejects([&] { characters::countCharacters(text); });
    auto path = folder / "input.txt";
    for (const auto& text : {std::string("Hello"), std::string("Hello\n"), std::string("Hello\r\n"),
                             std::string("\xEF\xBB\xBFHello\r\n")}) {
        practice::writeText(path, text);
        check(characters::readString(path) == "Hello", "Optional BOM and final line ending");
    }
    for (const auto& text : {"", "\n", "\r\n", "first\nsecond", "first\n\n"}) {
        practice::writeText(path, text); rejects([&] { characters::readString(path); });
    }
    auto report = characters::reportText(frequencies);
    check(report.find("U+0020\tSPACE\t1\n") != std::string::npos &&
          report.find("U+0009\tTAB\t1\n") != std::string::npos, "Readable whitespace report");
    check(report.find("U+0041\tA\t1\n") < report.find("U+0061\ta\t2\n"), "Code-point output order");
    check(characters::countCharacters(std::string(characters::maxTextBytes, 'A')).at(U'A') ==
          characters::maxTextBytes, "Text capacity boundary");
    rejects([&] { characters::countCharacters(std::string(characters::maxTextBytes + 1, 'A')); });
}

void ioChecks(const std::filesystem::path& folder) {
    auto input = folder / "protected.txt";
    practice::writeText(input, "Do not replace this input.");
    rejects([&] { practice::checkOutputs(input, {input}); });
    rejects([&] { practice::checkOutputs({}, {folder / "same.txt", folder / "." / "same.txt"}); });
    rejects([&] { practice::checkOutputs({}, {folder / "missing" / "out.txt"}); });
    rejects([&] { practice::checkOutputs({}, {folder}); });
    rejects([&] { practice::checkOutputs({}, {std::filesystem::path()}); });
    rejects([&] { practice::readBytes(folder / "missing.txt", 10); });
    rejects([&] { practice::readBytes(input, 3); });
    check(practice::readBytes(input, 100) == "Do not replace this input.", "Inputs unchanged after rejected paths");
}

int main() {
    auto stamp = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    auto folder = std::filesystem::temp_directory_path() / ("practice-tests-" + std::to_string(stamp));
    try {
        std::filesystem::create_directory(folder);
        sortingChecks(folder); characterChecks(folder); ioChecks(folder);
        // Remove only the flat set of fixtures created by this test process.
        for (const auto& entry : std::filesystem::directory_iterator(folder)) {
            if (!entry.is_regular_file()) throw std::runtime_error("Unexpected test fixture type.");
            std::filesystem::remove(entry.path());
        }
        std::filesystem::remove(folder);
        std::cout << "PASS: " << checks << " core checks.\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\nTest fixtures retained at " << folder << '\n'; return 1;
    }
    return 0;
}
