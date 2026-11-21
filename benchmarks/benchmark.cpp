#include "../src/merge_sort.hpp"
#include <algorithm>
#include <chrono>
#include <random>

namespace {
constexpr int repetitions = 9;
constexpr unsigned seed = 20261121;
using Clock = std::chrono::steady_clock;

std::vector<double> makeInput(std::size_t count, const std::string& pattern) {
    std::mt19937 generator(seed + static_cast<unsigned>(count));
    std::vector<double> values(count);
    for (double& value : values)
        value = pattern == "few_unique" ? static_cast<double>(generator() % 8) / 2.0
            : static_cast<double>(generator() % 2000001) / 1000.0 - 1000.0;
    if (pattern == "sorted" || pattern == "reverse") std::sort(values.begin(), values.end());
    if (pattern == "reverse") std::reverse(values.begin(), values.end());
    return values;
}

int batchSize(std::size_t count) {
    if (count <= 100) return 128;
    if (count <= 1000) return 32;
    if (count <= 10000) return 4;
    return 1;
}

double measure(const std::vector<double>& input, const std::vector<double>& expected,
               const std::string& algorithm) {
    const int batch = batchSize(input.size());
    std::vector<std::vector<double>> copies(static_cast<std::size_t>(batch), input);
    const auto start = Clock::now();
    for (auto& values : copies) {
        if (algorithm == "merge_sort") sorting::mergeSort(values);
        else std::sort(values.begin(), values.end());
    }
    const auto finish = Clock::now();
    for (const auto& values : copies)
        if (values != expected) throw std::runtime_error("Benchmark produced an incorrect result.");
    return std::chrono::duration<double, std::micro>(finish - start).count() / batch;
}

std::uint64_t comparisons(const std::vector<double>& input, const std::string& algorithm) {
    auto values = input;
    if (algorithm == "merge_sort") {
        sorting::Metrics metrics;
        sorting::mergeSort(values, &metrics);
        return metrics.comparisons;
    }
    std::uint64_t count = 0;
    std::sort(values.begin(), values.end(), [&count](double a, double b) { ++count; return a < b; });
    return count;
}
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: benchmark output-prefix\nWrites prefix_raw.csv and prefix_summary.csv.\n";
        return 1;
    }
    try {
        auto prefix = std::string(argv[1]);
        std::filesystem::path rawPath = prefix + "_raw.csv";
        std::filesystem::path summaryPath = prefix + "_summary.csv";
        practice::checkOutputs({}, {rawPath, summaryPath});
        std::ostringstream raw;
        std::ostringstream summary;
        raw.imbue(std::locale::classic()); summary.imbue(std::locale::classic());
        raw << "pattern,n,algorithm,repetition,batch,microseconds\n" << std::setprecision(10);
        summary << "pattern,n,algorithm,repetitions,batch,median_us,q1_us,q3_us,min_us,max_us,comparisons\n"
                << std::setprecision(10);
        const std::vector<std::string> algorithms = {"merge_sort", "std_sort"};
        for (const auto& pattern : {"random", "sorted", "reverse", "few_unique"}) {
            for (std::size_t count : {100u, 1000u, 10000u, 100000u, 1000000u}) {
                const auto input = makeInput(count, pattern);
                auto expected = input;
                std::sort(expected.begin(), expected.end());
                for (const auto& algorithm : algorithms) measure(input, expected, algorithm);
                std::vector<double> times[2];
                for (int repetition = 0; repetition < repetitions; ++repetition) {
                    // Alternate order to reduce systematic warm-cache/order bias.
                    for (int turn = 0; turn < 2; ++turn) {
                        int index = (repetition + turn) % 2;
                        auto elapsed = measure(input, expected, algorithms[static_cast<std::size_t>(index)]);
                        times[index].push_back(elapsed);
                        raw << pattern << ',' << count << ',' << algorithms[static_cast<std::size_t>(index)]
                            << ',' << repetition + 1 << ',' << batchSize(count) << ',' << elapsed << '\n';
                    }
                }
                for (std::size_t index = 0; index < algorithms.size(); ++index) {
                    auto& values = times[index];
                    std::sort(values.begin(), values.end());
                    summary << pattern << ',' << count << ',' << algorithms[index] << ',' << repetitions
                            << ',' << batchSize(count) << ',' << values[4] << ',' << values[2]
                            << ',' << values[6] << ',' << values.front() << ',' << values.back()
                            << ',' << comparisons(input, algorithms[index]) << '\n';
                }
                std::cout << "Verified " << pattern << ", N=" << count << '\n';
            }
        }
        practice::writeText(rawPath, raw.str());
        practice::writeText(summaryPath, summary.str());
        std::cout << "Benchmark complete: 360 timed batches, 9 repetitions per configuration.\n"
                  << "Seed: " << seed << ". Copying, file I/O and validation of results are outside timing.\n"
                  << "Merge-sort input validation and scratch allocation are inside timing.\n";
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n'; return 1;
    }
    return 0;
}
