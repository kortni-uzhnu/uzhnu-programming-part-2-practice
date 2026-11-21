#include "character_frequency.hpp"

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string(argv[1]) == "--help") {
        std::cout << "Usage: character_frequency [input.txt report.txt]\n"
                  << "Input: one UTF-8 text line, with an optional final LF or CRLF.\n";
        return 0;
    }
    try {
        std::filesystem::path inputPath;
        std::filesystem::path outputPath;
        if (argc == 3) { inputPath = argv[1]; outputPath = argv[2]; }
        else if (argc == 1) {
            std::cout << "Character frequency analysis\n";
            inputPath = practice::prompt("Input filename [input.txt]: ", "input.txt");
            outputPath = practice::prompt("Report filename [report.txt]: ", "report.txt");
        } else throw std::runtime_error("Usage: character_frequency [input.txt report.txt]");
        auto input = characters::readString(inputPath);
        auto frequencies = characters::countCharacters(input);
        practice::checkOutputs(inputPath, {outputPath});
        practice::writeText(outputPath, characters::reportText(frequencies));
        std::size_t total = 0;
        for (const auto& entry : frequencies) total += entry.second;
        std::cout << "Characters counted: " << total << "\nDistinct characters: " << frequencies.size()
                  << "\nReport saved to " << outputPath.string() << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
