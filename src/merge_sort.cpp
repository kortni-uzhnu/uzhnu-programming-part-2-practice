#include "merge_sort.hpp"

namespace {
std::vector<double> keyboardArray() {
    auto count = sorting::parseCount(practice::prompt("Number of elements (0-1000000): "));
    std::vector<double> values;
    values.reserve(count);
    if (count != 0) std::cout << "Enter " << count << " real numbers, separated by spaces or newlines:\n";
    while (values.size() < count) {
        std::istringstream line(practice::prompt(""));
        std::string word;
        while (line >> word) {
            if (values.size() == count) throw std::runtime_error("More values entered than declared.");
            values.push_back(sorting::parseReal(word));
        }
    }
    return values;
}

void usage() {
    std::cout << "Usage: merge_sort\n"
              << "   or: merge_sort --file input.txt original.txt sorted.txt\n"
              << "File format: element count N, then exactly N finite real numbers.\n";
}
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string(argv[1]) == "--help") { usage(); return 0; }
    try {
        std::vector<double> original;
        std::filesystem::path inputPath;
        std::filesystem::path originalPath;
        std::filesystem::path sortedPath;
        if (argc == 5 && std::string(argv[1]) == "--file") {
            inputPath = argv[2]; originalPath = argv[3]; sortedPath = argv[4];
            original = sorting::loadArray(inputPath);
        } else if (argc == 1) {
            std::cout << "Merge sort\n1. Keyboard input\n2. File input\n";
            auto choice = practice::prompt("Choice: ");
            if (choice == "1") original = keyboardArray();
            else if (choice == "2") {
                inputPath = practice::prompt("Input filename: ");
                original = sorting::loadArray(inputPath);
            } else throw std::runtime_error("Choose 1 for keyboard input or 2 for file input.");
            originalPath = practice::prompt("Save original array as [original_array.txt]: ", "original_array.txt");
            sortedPath = practice::prompt("Save sorted array as [sorted_array.txt]: ", "sorted_array.txt");
        } else { usage(); return 1; }
        practice::checkOutputs(inputPath, {originalPath, sortedPath});
        auto sorted = original;
        sorting::Metrics metrics;
        sorting::mergeSort(sorted, &metrics);
        practice::writeText(originalPath, sorting::arrayText(original));
        std::cout << "Original array saved to " << originalPath.string() << '\n';
        practice::writeText(sortedPath, sorting::arrayText(sorted));
        std::cout << "Sorted array (" << sorted.size() << " elements):\n";
        for (std::size_t i = 0; i < sorted.size() && i < 20; ++i) std::cout << sorted[i] << ' ';
        if (sorted.size() > 20) std::cout << "... (full array in the output file)";
        std::cout << "\nSorted array saved to " << sortedPath.string()
                  << "\nElement comparisons: " << metrics.comparisons << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
