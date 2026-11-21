# Programming, part 2 - Training Practice

Two C++17 console programs and a combined practice report for UzhNU.

## Programs

### Task 1: merge sort

`src/merge_sort.cpp` sorts a dynamically allocated `std::vector<double>` using
an implemented recursive merge sort. It accepts keyboard or file input, saves
the original array, and saves the sorted array separately. Equal values keep
their original order. The console previews up to 20 sorted values; the output
file contains the complete array.

The numeric file format is an integer count followed by exactly that many
finite real numbers, separated by whitespace. Counts from 0 to 1,000,000 are
supported. Decimal points use `.` and scientific notation is accepted. Input
files are limited to 64 MiB. Output uses enough precision for a double to make
an exact save/load round trip, including subnormal values and signed zero.

```text
8
3.5 -2 0 3.5 10 -7.25 1.125 4
```

Run without arguments for prompts, or provide all filenames:

```powershell
.\build\merge_sort.exe --file examples\numbers.txt original_array.txt sorted_array.txt
```

Keyboard mode accepts the element count on its own line, followed by the values
on one or more lines. An invalid entry cancels that operation with an error.

### Task 2: character frequency

`src/character_frequency.cpp` reads one UTF-8 text line and writes a frequency
report containing every distinct Unicode code point and its occurrence count.
It includes spaces, punctuation, tabs and both letter cases. Ukrainian letters
and four-byte characters are supported. Output rows are ordered by code point.

```powershell
.\build\character_frequency.exe examples\input.txt report.txt
```

Run without arguments to enter filenames. The defaults are `input.txt` and
`report.txt`. The input may have an initial UTF-8 BOM and one final LF or CRLF;
those file-format markers are excluded from the counts. Extra lines, empty
strings, invalid UTF-8, and strings larger than 4 MiB are rejected. A string made
only of spaces is valid. A bare carriage return inside the string is counted.

The report is UTF-8 tab-separated text:

```text
Code point  Character  Count
U+0020      SPACE      1
U+0041      A          1
U+0061      a          2
```

The actual separators are tabs. Controls are labelled `CONTROL`, with the code
point distinguishing them; tabs are labelled `TAB`. Counting uses code points,
not visual grapheme clusters. It performs no normalization or case folding, so
`A` and `a` differ, and a combining accent is counted separately from its letter.

### File handling

Both programs check input and output paths and report file errors. An output
must not replace its input, and Task 1's two output paths must be different.
Output folders must already exist. Existing output files are overwritten.
These are ordinary checked file writes, not database transactions: a disk or
permission failure can leave a partial output, and Task 1 may have saved the
original array before a later sorted-output write fails. Keep source files and
important data outside the chosen output paths.

## Building

Only the C++17 standard library is used. No third-party C++ libraries, database,
GUI toolkit or package manager is needed. Keep the files in `src/` together.
The programs use headers beside their `.cpp` files, so they are built separately.
Run these commands from the project folder after making a `build` directory:

```powershell
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 src/merge_sort.cpp -o build/merge_sort.exe
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 src/character_frequency.cpp -o build/character_frequency.exe
```

With a Microsoft C++ Developer Command Prompt:

```bat
cl /std:c++17 /EHsc /W4 /utf-8 src\merge_sort.cpp /Fe:build\merge_sort.exe
cl /std:c++17 /EHsc /W4 /utf-8 src\character_frequency.cpp /Fe:build\character_frequency.exe
```

On Linux, omit `.exe` and run binaries with `./build/merge_sort` and
`./build/character_frequency`. A modern compiler with C++17 floating-point
`std::from_chars` support is required. Both programs also support `--help`.

CMake is an optional build route:

```sh
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

## Tests

```powershell
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 tests/core_tests.cpp -o build/practice_tests.exe
.\build\practice_tests.exe
python tests/cli_tests.py --bin-dir build
```

Python 3 is needed only for the optional end-to-end test script. That script
uses its standard library. The recorded test results are in `docs/test_results.json`
and `docs/Verification.txt`. All 992 core checks and 68 end-to-end cases passed
on Linux in the local WSL environment. The core checks use independent sorting
and counting oracles, and the console tests compare actual saved files.

Windows and Linux versions of both programs, the tests and the benchmark
compiled cleanly with warnings treated as errors. Native Windows execution of
the sorter and test harness was blocked by Application Control on this machine.
Full Windows runtime verification was therefore not completed. The Windows
character program's help command did run. No security settings were changed.

## Timing experiment

```powershell
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 benchmarks/benchmark.cpp -o build/benchmark.exe
.\build\benchmark.exe benchmarks\rerun
```

The benchmark compares the implemented merge sort with `std::sort`, using
100, 1,000, 10,000, 100,000 and 1,000,000 elements. It tests random, sorted,
reverse-sorted and few-distinct-value inputs generated with seed 20261121.
Each configuration has one warm-up and nine measured repetitions, with the
algorithm order alternating. Small inputs are sorted in batches, and elapsed
time is divided by batch size to report microseconds per sort.

Input generation, input copying, reference sorting, file I/O, comparison-count
passes and result checks are excluded from timing. Merge sort's finite-value
validation and scratch-buffer allocation are included. This measures these
specific implementations, not identical internal work. The benchmark checks
every sorted result after timing. Comparator calls are counted separately.

The recorded Linux run is in `benchmarks/linux_raw.csv` and
`benchmarks/linux_summary.csv`: 360 measured batches, 40 summary rows, and
9 repetitions for every algorithm/pattern/size combination. Summary rows contain
median, first and third quartiles, minimum, maximum and element-comparison counts.
`benchmarks/metadata.json` describes the environment and source hashes. The report
includes the results, plots, interpretation and limitations. Timing depends on
hardware and background activity; these numbers are not universal speed claims.

## Report and files

- `docs/Practice_Report.pdf` - the combined report for review, within Moodle's
  one-PDF, 5 MB limit.
- `docs/build_report.py` - editable report content and generator. Requires
  Python, ReportLab and Matplotlib only when rebuilding the document and plots.
- `docs/figures/` - exported timing and operation-count plots.
- `examples/` - numeric, English and Ukrainian input samples.
- `src/` - both applications and their shared/core headers.
- `tests/` - direct C++ checks and Python console cases.
- `benchmarks/` - benchmark source, raw observations, summary and metadata.
- `build/` - local Windows/Linux binaries, excluded from Git.

Task for Practice: https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=74000

The selected interpretation follows the supplied task brief and practice example:
two separate programs and one combined report. The report includes technical
tasks, algorithms, development, tests and results, conclusions, references,
flowcharts, complete application source and benchmark source. Nothing in this
folder has been uploaded or submitted as part of its preparation.
