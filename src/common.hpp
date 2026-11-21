#ifndef PRACTICE_COMMON_HPP
#define PRACTICE_COMMON_HPP

#include <filesystem>
#include <fstream>
#include <iostream>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace practice {
namespace fs = std::filesystem;

inline std::string trim(const std::string& text) {
    auto first = text.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    return text.substr(first, text.find_last_not_of(" \t\r\n") - first + 1);
}

inline std::string prompt(const std::string& label, const std::string& fallback = "") {
    std::cout << label << std::flush;
    std::string text;
    if (!std::getline(std::cin, text)) throw std::runtime_error("Input ended before the operation was complete.");
    text = trim(text);
    return text.empty() ? fallback : text;
}

inline std::string readBytes(const fs::path& path, std::size_t limit) {
    if (!fs::is_regular_file(path)) throw std::runtime_error("Input is missing or is not a regular file.");
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Cannot open the input file.");
    std::string bytes;
    char buffer[4096];
    while (input.read(buffer, sizeof buffer) || input.gcount() != 0) {
        auto count = static_cast<std::size_t>(input.gcount());
        if (count > limit - bytes.size()) throw std::runtime_error("Input file exceeds the size limit.");
        bytes.append(buffer, count);
    }
    if (input.bad()) throw std::runtime_error("Could not finish reading the input file.");
    return bytes;
}

inline bool samePath(const fs::path& left, const fs::path& right) {
    if (fs::exists(left) && fs::exists(right)) return fs::equivalent(left, right);
    return fs::weakly_canonical(fs::absolute(left)) == fs::weakly_canonical(fs::absolute(right));
}

inline void checkOutputs(const fs::path& input, const std::vector<fs::path>& outputs) {
    for (std::size_t i = 0; i < outputs.size(); ++i) {
        const auto& path = outputs[i];
        if (path.empty() || path.filename().empty()) throw std::runtime_error("Output filename cannot be empty.");
        auto parent = fs::absolute(path).parent_path();
        if (!fs::is_directory(parent)) throw std::runtime_error("Output folder does not exist.");
        if (fs::exists(path) && !fs::is_regular_file(path))
            throw std::runtime_error("Output must be a regular file.");
        if (!input.empty() && samePath(input, path))
            throw std::runtime_error("An output file must not replace the input file.");
        for (std::size_t j = 0; j < i; ++j)
            if (samePath(outputs[j], path)) throw std::runtime_error("Output filenames must be different.");
    }
}

inline void writeText(const fs::path& path, const std::string& text) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("Cannot open output file: " + path.string());
    output.write(text.data(), static_cast<std::streamsize>(text.size()));
    output.close();
    if (!output) throw std::runtime_error("Could not finish writing output file: " + path.string());
}
} // namespace practice
#endif
