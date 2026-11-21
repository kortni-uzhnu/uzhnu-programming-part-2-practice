#ifndef PRACTICE_CHARACTER_FREQUENCY_HPP
#define PRACTICE_CHARACTER_FREQUENCY_HPP

#include "common.hpp"
#include <cstdint>
#include <iomanip>
#include <map>

namespace characters {
constexpr std::size_t maxTextBytes = 4 * 1024 * 1024;
using Frequencies = std::map<char32_t, std::size_t>;

inline std::string readString(const std::filesystem::path& path) {
    auto text = practice::readBytes(path, maxTextBytes + 5);
    if (text.compare(0, 3, "\xEF\xBB\xBF") == 0) text.erase(0, 3);
    auto newline = text.find('\n');
    if (newline != std::string::npos) {
        if (newline + 1 != text.size()) throw std::runtime_error("Input must contain one line of text only.");
        text.pop_back();
        if (!text.empty() && text.back() == '\r') text.pop_back();
    }
    if (text.empty()) throw std::runtime_error("The input string is empty.");
    if (text.size() > maxTextBytes) throw std::runtime_error("The input string exceeds 4 MiB.");
    return text;
}

inline Frequencies countCharacters(const std::string& text) {
    if (text.empty()) throw std::runtime_error("The input string is empty.");
    if (text.size() > maxTextBytes) throw std::runtime_error("The input string exceeds 4 MiB.");
    Frequencies frequencies;
    for (std::size_t i = 0; i < text.size();) {
        auto first = static_cast<unsigned char>(text[i++]);
        char32_t code = 0;
        std::size_t continuation = 0;
        char32_t minimum = 0;
        if (first < 0x80) code = first;
        else if (first >= 0xC2 && first <= 0xDF) { code = first & 0x1F; continuation = 1; minimum = 0x80; }
        else if (first >= 0xE0 && first <= 0xEF) { code = first & 0x0F; continuation = 2; minimum = 0x800; }
        else if (first >= 0xF0 && first <= 0xF4) { code = first & 0x07; continuation = 3; minimum = 0x10000; }
        else throw std::runtime_error("Input is not valid UTF-8.");
        for (std::size_t j = 0; j < continuation; ++j) {
            if (i == text.size()) throw std::runtime_error("Input contains an incomplete UTF-8 sequence.");
            auto next = static_cast<unsigned char>(text[i++]);
            if ((next & 0xC0) != 0x80) throw std::runtime_error("Input is not valid UTF-8.");
            code = (code << 6) | (next & 0x3F);
        }
        if (code < minimum || code > 0x10FFFF || (code >= 0xD800 && code <= 0xDFFF))
            throw std::runtime_error("Input contains an invalid UTF-8 code point.");
        ++frequencies[code];
    }
    return frequencies;
}

inline std::string utf8(char32_t code) {
    std::string result;
    if (code < 0x80) result += static_cast<char>(code);
    else if (code < 0x800) {
        result += static_cast<char>(0xC0 | (code >> 6));
        result += static_cast<char>(0x80 | (code & 0x3F));
    } else if (code < 0x10000) {
        result += static_cast<char>(0xE0 | (code >> 12));
        result += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
        result += static_cast<char>(0x80 | (code & 0x3F));
    } else {
        result += static_cast<char>(0xF0 | (code >> 18));
        result += static_cast<char>(0x80 | ((code >> 12) & 0x3F));
        result += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
        result += static_cast<char>(0x80 | (code & 0x3F));
    }
    return result;
}

inline std::string reportText(const Frequencies& frequencies) {
    std::ostringstream report;
    report << "Code point\tCharacter\tCount\n";
    for (const auto& entry : frequencies) {
        auto code = entry.first;
        report << "U+" << std::uppercase << std::hex << std::setfill('0') << std::setw(4)
               << static_cast<std::uint32_t>(code) << std::dec << '\t';
        if (code == U' ') report << "SPACE";
        else if (code == U'\t') report << "TAB";
        else if (code < 32 || (code >= 0x7F && code <= 0x9F)) report << "CONTROL";
        else report << utf8(code);
        report << '\t' << entry.second << '\n';
    }
    return report.str();
}
} // namespace characters
#endif
