#ifndef PRACTICE_MERGE_SORT_HPP
#define PRACTICE_MERGE_SORT_HPP

#include "common.hpp"
#include <charconv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>

namespace sorting {
constexpr std::size_t maxElements = 1000000;
struct Metrics { std::uint64_t comparisons = 0; std::uint64_t writes = 0; };

inline std::size_t parseCount(const std::string& text) {
    if (text.empty()) throw std::runtime_error("Enter an integer element count from 0 to 1000000.");
    std::size_t count = 0;
    for (char c : text) {
        if (c < '0' || c > '9') throw std::runtime_error("Enter an integer element count from 0 to 1000000.");
        count = count * 10 + static_cast<unsigned>(c - '0');
        if (count > maxElements) throw std::runtime_error("Element count exceeds 1000000.");
    }
    return count;
}

inline double parseReal(const std::string& text) {
    double value = 0;
    const char* begin = text.data();
    const char* end = begin + text.size();
    if (begin != end && *begin == '+') ++begin;
    auto result = std::from_chars(begin, end, value, std::chars_format::general);
    if (result.ec != std::errc() || !std::isfinite(value))
        throw std::runtime_error("Each array element must be a finite real number.");
    if (result.ptr != end) throw std::runtime_error("A number contains extra characters.");
    return value;
}

inline std::vector<double> loadArray(const std::filesystem::path& path) {
    std::istringstream input(practice::readBytes(path, 64 * 1024 * 1024));
    std::string word;
    if (!(input >> word)) throw std::runtime_error("The array file is empty.");
    std::vector<double> values(parseCount(word));
    for (double& value : values) {
        if (!(input >> word)) throw std::runtime_error("The array file contains fewer values than declared.");
        value = parseReal(word);
    }
    if (input >> word) throw std::runtime_error("The array file contains extra data.");
    return values;
}

inline void mergeRange(std::vector<double>& values, std::vector<double>& buffer,
                       std::size_t begin, std::size_t end, Metrics* metrics) {
    if (end - begin < 2) return;
    const auto middle = begin + (end - begin) / 2;
    mergeRange(values, buffer, begin, middle, metrics);
    mergeRange(values, buffer, middle, end, metrics);
    auto left = begin;
    auto right = middle;
    auto position = begin;
    while (left < middle && right < end) {
        if (metrics) ++metrics->comparisons;
        buffer[position++] = values[left] <= values[right] ? values[left++] : values[right++];
    }
    while (left < middle) buffer[position++] = values[left++];
    while (right < end) buffer[position++] = values[right++];
    for (auto i = begin; i < end; ++i) values[i] = buffer[i];
    if (metrics) metrics->writes += 2 * (end - begin);
}

inline void mergeSort(std::vector<double>& values, Metrics* metrics = nullptr) {
    if (metrics) *metrics = {};
    if (values.size() > maxElements) throw std::runtime_error("Array exceeds the supported element count.");
    for (double value : values)
        if (!std::isfinite(value)) throw std::runtime_error("Sorting requires finite real numbers.");
    std::vector<double> buffer(values.size());
    mergeRange(values, buffer, 0, values.size(), metrics);
}

inline std::string arrayText(const std::vector<double>& values) {
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << values.size() << '\n' << std::setprecision(std::numeric_limits<double>::max_digits10);
    for (std::size_t i = 0; i < values.size(); ++i)
        output << values[i] << (i + 1 == values.size() ? '\n' : ' ');
    return output.str();
}
} // namespace sorting
#endif
