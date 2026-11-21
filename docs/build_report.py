"""Build the practice report and figures with ReportLab and Matplotlib."""
import csv
import hashlib
import json
import math
from pathlib import Path
import textwrap
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, PageBreak,
                               PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
FIGURES = DOCS / 'figures'
FIGURES.mkdir(exist_ok=True)
TESTS = json.loads((DOCS / 'test_results.json').read_text(encoding='utf-8'))
META = json.loads((ROOT / 'benchmarks' / 'metadata.json').read_text(encoding='utf-8'))
DEMO = json.loads((DOCS / 'demo_sessions.json').read_text(encoding='utf-8'))
ROWS = list(csv.DictReader((ROOT / 'benchmarks' / 'linux_summary.csv').open()))
assert TESTS['execution_cases_passed'] == 68 and len(ROWS) == 40
assert all(row['status'] == 'PASS' for row in TESTS['results'])
for name, digest in TESTS['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
for name, digest in META['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def row(pattern, count, algorithm):
    return next(item for item in ROWS if item['pattern'] == pattern and
                int(item['n']) == count and item['algorithm'] == algorithm)


def make_plots():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'axes.spines.top': False, 'axes.spines.right': False})
    palette = {'merge_sort': '#145a85', 'std_sort': '#b3481e'}
    names = {'merge_sort': 'Implemented merge sort', 'std_sort': 'std::sort'}
    sizes = META['sizes']
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.5), layout='constrained')
    for ax, pattern in zip(axes.flat, META['patterns']):
        for algorithm in ['merge_sort', 'std_sort']:
            records = [row(pattern, n, algorithm) for n in sizes]
            ax.plot(sizes, [float(r['median_us']) for r in records], marker='o',
                    markersize=3, linewidth=1.5, color=palette[algorithm], label=names[algorithm])
            ax.fill_between(sizes, [float(r['q1_us']) for r in records],
                            [float(r['q3_us']) for r in records], color=palette[algorithm], alpha=.16)
        ax.set(xscale='log', yscale='log', xlabel='Array size N', ylabel='Microseconds per sort',
               title=pattern.replace('_', ' ').capitalize())
        ax.grid(True, which='major', alpha=.18)
    axes[0, 0].legend(fontsize=7, loc='upper left')
    fig.savefig(FIGURES / 'timing.png', dpi=220, facecolor='white')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 3.6), layout='constrained')
    for algorithm in ['merge_sort', 'std_sort']:
        ax.plot(sizes, [int(row('random', n, algorithm)['comparisons']) for n in sizes],
                marker='o', linewidth=1.6, color=palette[algorithm], label=names[algorithm])
    ax.plot(sizes, [n * math.log2(n) for n in sizes], '--', color='#666666', label='N log2(N) reference')
    ax.set(xscale='log', yscale='log', xlabel='Array size N', ylabel='Element comparisons',
           title='Comparison counts on the random input')
    ax.legend(fontsize=8); ax.grid(True, alpha=.18)
    fig.savefig(FIGURES / 'comparisons.png', dpi=220, facecolor='white')
    plt.close(fig)


def register_fonts():
    choices = [
        (Path('C:/Windows/Fonts'), ['times.ttf', 'timesbd.ttf', 'timesi.ttf', 'consola.ttf']),
        (Path('/usr/share/fonts/truetype/dejavu'),
         ['DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf', 'DejaVuSerif-Italic.ttf', 'DejaVuSansMono.ttf']),
    ]
    for folder, files in choices:
        if all((folder / file).exists() for file in files):
            for name, file in zip(['Body', 'BodyBold', 'BodyItalic', 'Code'], files):
                pdfmetrics.registerFont(TTFont(name, str(folder / file)))
            pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic')
            return
    raise RuntimeError('Times New Roman/Consolas or DejaVu fonts are required.')


register_fonts()
styles = {
    'Text': ParagraphStyle('Text', fontName='Body', fontSize=12, leading=16,
                           alignment=TA_JUSTIFY, spaceAfter=9),
    'H1': ParagraphStyle('H1', fontName='BodyBold', fontSize=14, leading=18,
                         spaceAfter=13, keepWithNext=True),
    'H2': ParagraphStyle('H2', fontName='BodyBold', fontSize=12, leading=16,
                         spaceBefore=7, spaceAfter=9, keepWithNext=True),
    'File': ParagraphStyle('File', fontName='BodyBold', fontSize=11, leading=15,
                           spaceBefore=10, spaceAfter=8, keepWithNext=True),
    'Center': ParagraphStyle('Center', fontName='Body', fontSize=12, leading=17,
                             alignment=TA_CENTER, spaceAfter=10),
    'Title': ParagraphStyle('Title', fontName='BodyBold', fontSize=17, leading=23,
                            alignment=TA_CENTER, spaceAfter=14),
    'Small': ParagraphStyle('Small', fontName='Body', fontSize=10, leading=13, spaceAfter=8),
    'Cell': ParagraphStyle('Cell', fontName='Body', fontSize=10, leading=12.5),
    'Caption': ParagraphStyle('Caption', fontName='BodyItalic', fontSize=10.5, leading=13,
                              alignment=TA_CENTER, spaceBefore=6, spaceAfter=12),
    'Code': ParagraphStyle('Code', fontName='Code', fontSize=7.5, leading=9.8, spaceAfter=7),
    'Terminal': ParagraphStyle('Terminal', fontName='Code', fontSize=8.5, leading=11.5,
                               spaceBefore=6, spaceAfter=12),
}


class Report(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ('H1', 'H2'):
            text = flowable.getPlainText()
            if text == 'Contents':
                return
            level = 0 if flowable.style.name == 'H1' else 1
            key = 'heading-' + str(self.seq.nextf('heading'))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
            self.notify('TOCEntry', (level, text, self.page, key))


def decorate(canvas, document):
    if document.page == 1:
        return
    canvas.saveState()
    canvas.setFont('Body', 9)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(25 * mm, A4[1] - 14 * mm, 'Programming training practice | Merge sort and character frequency')
    canvas.setStrokeColor(colors.HexColor('#b8bdc1'))
    canvas.line(25 * mm, A4[1] - 16 * mm, A4[0] - 20 * mm, A4[1] - 16 * mm)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, str(document.page))
    canvas.restoreState()


class Flowchart(Flowable):
    def __init__(self, kind):
        Flowable.__init__(self)
        self.kind = kind
        self.width = 460
        self.height = 510

    def draw(self):
        c = self.canv
        c.setLineWidth(.9); c.setStrokeColor(colors.HexColor('#263e4b'))

        def label(x, y, text):
            lines = text.split('\n')
            c.setFont('Body', 10); c.setFillColor(colors.black)
            for i, line in enumerate(lines):
                c.drawCentredString(x, y + (len(lines) - 1) * 6 - i * 12 - 3, line)

        def box(x, y, w, h, text, rounded=False):
            c.setFillColor(colors.HexColor('#f4f7f8'))
            c.roundRect(x, y, w, h, 9 if rounded else 0, fill=1)
            label(x + w / 2, y + h / 2, text)

        def diamond(x, y, w, h, text):
            path = c.beginPath(); path.moveTo(x, y + h / 2)
            path.lineTo(x + w / 2, y + h); path.lineTo(x + w, y + h / 2)
            path.lineTo(x + w / 2, y); path.close()
            c.setFillColor(colors.white); c.drawPath(path, fill=1)
            label(x + w / 2, y + h / 2, text)

        def arrow(points, text=None, where=None):
            path = c.beginPath(); path.moveTo(*points[0])
            for point in points[1:]: path.lineTo(*point)
            c.drawPath(path)
            (a, b), (x, y) = points[-2:]
            if abs(x - a) > abs(y - b):
                sign = 1 if x > a else -1
                c.line(x, y, x - sign * 5, y - 3); c.line(x, y, x - sign * 5, y + 3)
            else:
                sign = 1 if y > b else -1
                c.line(x, y, x - 3, y - sign * 5); c.line(x, y, x + 3, y - sign * 5)
            if text:
                c.setFont('Body', 9); c.drawString(*(where or points[0]), text)

        if self.kind == 'sort_program':
            box(150, 473, 160, 30, 'Start', True)
            box(130, 414, 200, 37, 'Choose keyboard or file input')
            box(15, 344, 180, 40, 'Read N and values\nfrom the keyboard')
            box(265, 344, 180, 40, 'Read N and values\nfrom the input file')
            box(125, 273, 210, 43, 'Validate array\nCheck distinct output paths')
            box(125, 201, 210, 43, 'Copy original array\nRun merge sort on the copy')
            box(125, 129, 210, 43, 'Save original array\nSave sorted array')
            box(125, 60, 210, 40, 'Display preview and comparisons')
            box(150, 3, 160, 30, 'End', True)
            arrow([(230, 473), (230, 451)])
            arrow([(160, 414), (160, 400), (105, 400), (105, 384)], 'Keyboard', (55, 402))
            arrow([(300, 414), (300, 400), (355, 400), (355, 384)], 'File', (361, 402))
            arrow([(105, 344), (105, 328), (230, 328), (230, 316)])
            arrow([(355, 344), (355, 328), (230, 328)])
            for top, bottom in [(273, 244), (201, 172), (129, 100), (60, 33)]:
                arrow([(230, top), (230, bottom)])
        elif self.kind == 'merge':
            box(140, 472, 180, 32, 'mergeRange(begin, end)', True)
            diamond(155, 382, 150, 65, 'Fewer than 2 values?')
            box(355, 398, 100, 33, 'Return', True)
            box(130, 310, 200, 44, 'Find midpoint\nSort left half recursively')
            box(130, 238, 200, 43, 'Sort right half recursively')
            box(110, 151, 240, 58, 'Merge into buffer\nTake left value on equality\nAppend the remaining values')
            box(130, 80, 200, 43, 'Copy merged range back')
            box(150, 15, 160, 33, 'Return', True)
            arrow([(230, 472), (230, 447)])
            arrow([(305, 414), (355, 414)], 'Yes', (319, 424))
            arrow([(230, 382), (230, 354)], 'No', (241, 366))
            for top, bottom in [(310, 281), (238, 209), (151, 123), (80, 48)]:
                arrow([(230, top), (230, bottom)])
        else:
            box(140, 473, 180, 31, 'Start / choose filenames', True)
            box(115, 405, 230, 42, 'Read one UTF-8 line\nRemove optional BOM and LF/CRLF')
            box(125, 335, 210, 43, 'Decode next Unicode code point')
            diamond(160, 251, 140, 58, 'Valid sequence?')
            box(355, 260, 100, 40, 'Print error\nStop', True)
            box(125, 183, 210, 40, 'Increment that code point count')
            diamond(160, 99, 140, 58, 'More input bytes?')
            box(115, 29, 230, 42, 'Check output path\nWrite frequency report and finish')
            arrow([(230, 473), (230, 447)])
            arrow([(230, 405), (230, 378)])
            arrow([(230, 335), (230, 309)])
            arrow([(300, 280), (355, 280)], 'No', (318, 289))
            arrow([(230, 251), (230, 223)], 'Yes', (240, 235))
            arrow([(230, 183), (230, 157)])
            arrow([(160, 128), (70, 128), (70, 356), (125, 356)], 'Yes', (111, 138))
            arrow([(230, 99), (230, 71)], 'No', (241, 83))


story = []
def p(text, style='Text'): story.append(Paragraph(text, styles[style]))
def h(text, level=1): p(text, 'H1' if level == 1 else 'H2')
def new(): story.append(PageBreak())


def table(headers, rows, widths):
    cells = [[Paragraph('<b>' + escape(x) + '</b>', styles['Cell']) for x in headers]]
    cells += [[Paragraph(escape(str(x)).replace('\n', '<br/>'), styles['Cell']) for x in record] for record in rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8edf0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#bac2c7')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.extend([t, Spacer(1, 9)])


def terminal(text, caption=None):
    lines = []
    for line in text.splitlines():
        lines += textwrap.wrap(line, width=87, subsequent_indent='  ',
                               replace_whitespace=False, drop_whitespace=False) or ['']
    story.append(Preformatted('\n'.join(lines), styles['Terminal']))
    if caption: p(caption, 'Caption')


def picture(name, width, height, caption):
    story.append(Image(str(FIGURES / name), width=width, height=height))
    p(caption, 'Caption')


def compact_demo(name):
    # Replace only the long machine-specific directory prefix in actual captured output.
    text = DEMO[name]['stdout']
    prefix = '/mnt/host/c/Users/cshie/Desktop/UzhNU/Programming Part II Practice/'
    return text.replace(prefix, '')


p('MINISTRY OF EDUCATION AND SCIENCE OF UKRAINE', 'Center')
p('STATE HIGHER EDUCATIONAL INSTITUTION<br/>"UZHHOROD NATIONAL UNIVERSITY"', 'Center')
p('FACULTY OF ENGINEERING AND TECHNOLOGY<br/>DEPARTMENT OF COMPUTER SYSTEMS AND NETWORKS', 'Center')
story.append(Spacer(1, 36 * mm))
p('PROGRAMMING TRAINING<br/>PRACTICE REPORT', 'Title')
p('Merge sorting algorithm<br/>and character-frequency analysis', 'Title')
story.append(Spacer(1, 24 * mm))
p('Student: Кортні Шілдс Скаллі', 'Center')
p('Supervisor: Assistant Hedeon T. S.', 'Center')
story.append(Spacer(1, 15 * mm))
p('National scale ____________________<br/>Points ____________ ECTS grade ____________', 'Center')
story.append(Spacer(1, 24 * mm))
p('Uzhhorod - 2026', 'Center')
new()

h('Individual technical task')
p('<b>Discipline.</b> Educational practice in programming, Programming, part 2.')
p('<b>Objective.</b> Develop two separate C++ programs and document their algorithms, '
  'implementation, verification and experimental results. The technical requirements '
  'follow Task.pdf supplied with the Moodle practice assignment [1].')
table(['Task', 'Required work'], [
    ('1. Merge sort', 'Sort a one-dimensional array of N real numbers using merge sort. Support keyboard and file input, dynamic memory allocation, saving the entered array, input checks and screen error messages. Investigate efficiency using timing experiments and array sizes. Provide a flowchart.'),
    ('2. String manipulation', 'Read a character string from a file. Count each distinct character and generate a report file with its occurrence count. Use functions or procedures, examine the processing methods, and provide algorithm flowcharts.'),
    ('Practice report', 'Include the technical task, algorithm descriptions, development, test-case set, testing results, conclusions, references and appendices. The Moodle form accepts one PDF up to 5 MB [1].'),
], [104, 364])
p('This version saves both the original and sorted numeric arrays. For text, the '
  'input is one UTF-8 line, and a character is interpreted as a Unicode code point. '
  'The original brief does not prescribe encodings, filenames or exact collection '
  'limits; the choices used here are stated explicitly in this report.')
p('Prepared on 21 November 2026 for review before submission. The original Moodle '
  'deadline was 30 June 2026 at 23:59. No extension or submission is claimed.')
p('Student signature ____________________<br/>Supervisor signature ____________________', 'Small')
new()

h('Abstract')
p('This practice work consists of two C++17 console applications. The first implements '
  'stable recursive merge sort for a dynamically allocated array of real numbers. '
  'It accepts keyboard or file input, saves the original values and writes the sorted '
  'result to a separate file. The second reads a text string from a file and generates '
  'a frequency report for all distinct Unicode code points.')
p('Both applications are organised around small functions for input, processing and '
  'output. Standard-library containers manage memory. Numeric input is checked for '
  'valid size and finite values. The text program checks the file structure and '
  'UTF-8 encoding, and distinguishes ordinary letters, whitespace and punctuation.')
p('The application, direct tests and benchmark compiled for Windows and Linux with '
  'warnings treated as errors. Full execution verification took place in local Linux '
  'WSL and passed 992 direct checks and 68 console cases. Native Windows execution '
  'was not fully verified because Application Control blocked the sorter and test '
  'executable. That limitation is retained in the recorded results.')
p('The performance experiment compares the implemented merge sort with std::sort '
  'for five sizes and four input patterns. Nine timed repetitions per configuration '
  'produced 360 measured batches. The report presents medians, quartiles and comparison '
  'counts, explains the timed region and discusses the limits of the comparison.')
p('<b>Keywords:</b> C++, merge sort, dynamic array, UTF-8, character frequency, file '
  'input/output, validation, testing, performance measurement.')
new()

h('Contents')
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle('TOC0', fontName='Body', fontSize=11, leading=14, spaceBefore=3),
    ParagraphStyle('TOC1', fontName='Body', fontSize=10, leading=13, leftIndent=12, spaceBefore=1),
]
toc.tableStyle = TableStyle([
    ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
])
story.append(toc)
new()

h('Introduction')
p('Sorting numerical data and summarising text are common programming tasks. '
  'They exercise different parts of the same development process: reading data, '
  'choosing a representation, applying an algorithm, checking the result and '
  'writing output that can be examined independently.')
p('The first task provides a direct exercise in divide-and-conquer programming. '
  'An array is split into smaller ranges, each range is sorted recursively, and '
  'the ordered ranges are merged. Dynamic storage allows the same program to '
  'handle a small manually entered array or a much larger file.')
p('The second task analyses a string by counting its characters. An occurrence '
  'table is simple to describe, but its correctness depends on a clear definition '
  'of input. A Ukrainian letter occupies more than one byte in UTF-8. This '
  'implementation decodes the file before counting so that those letters are '
  'represented as individual code points rather than separate encoded bytes.')
p('The practice assignment requests an explanation of algorithms, program '
  'development, test cases and test results [1]. The supplied practice report '
  'example provides a useful organisational model [2]. The present report follows '
  'that model while describing the actual source files, output and measurements '
  'produced for this version.')
p('A performance experiment is included because successful sorting alone does '
  'not show how the work changes with array size. The experiment uses repeatable '
  'inputs, separates timed work from file access and records both execution time '
  'and element-comparison counts. A standard-library sorter serves as a practical '
  'baseline, with differences between the implementations stated.')
p('The applications use the standard C++17 library and run locally. The scope '
  'does not include a graphical interface, network service or persistent record '
  'database. The intended outcome is a small, explainable pair of programs with '
  'repeatable evidence of correctness and performance.')
new()

h('1 Analysis of the terms of reference')
table(['Requirement', 'Implementation and evidence'], [
    ('Real-number array and merge sorting', 'A vector<double> is sorted in ascending order by mergeRange and mergeSort. The application does not delegate its sort to std::sort.'),
    ('Keyboard and file input', 'Interactive mode offers both sources. A --file command supports repeatable file-based runs.'),
    ('Dynamic memory', 'The input, sorted copy and merge buffer are dynamically allocated vectors with automatic lifetime management.'),
    ('Save entered array', 'The original sequence is saved separately from the full sorted result.'),
    ('Checks and error messages', 'Malformed values, inconsistent counts, missing files and conflicting paths produce errors.'),
    ('Performance research', 'Five sizes, four patterns and two algorithms; timing distributions and comparison counts are retained.'),
    ('Character analysis from a file', 'One UTF-8 line is decoded and all distinct code points are counted, including spaces and punctuation.'),
    ('Character report and functions', 'The UTF-8 report has a code point, readable character label and count per row. Reading, counting and writing are separate functions.'),
    ('Documentation', 'Both tasks have workflow diagrams, source listings and described tests with observed results.'),
], [140, 328])
p('The implementation permits empty numeric arrays and limits their size to '
  '1,000,000 elements. Character input is limited to 4 MiB and one line. These '
  'bounds are explicit implementation decisions. The report does not treat '
  'sample filenames or the example document length as compulsory requirements.')
new()

h('2 Analysis of methods and approaches')
p('Merge sort is prescribed by the first task. A top-down recursive version '
  'was selected because its split, recursive calls and merge phase are easy to '
  'trace. The standard analysis gives order N log N time for ordinary comparison '
  'operations [3]. Stability depends on how equal elements are taken during '
  'merging; this implementation chooses the left element on equality.')
p('A vector was selected instead of a fixed-size array or a manually owned '
  'new[] allocation. It provides dynamically sized contiguous storage and '
  'automatic ownership [4]. An auxiliary vector is allocated once per sort '
  'call, and the recursive calls reuse it. This avoids allocating two temporary '
  'vectors at every recursive merge.')
table(['Decision', 'Alternatives considered', 'Reason for the choice'], [
    ('Merge sort', 'Insertion sort, quicksort, std::sort', 'Required algorithm. std::sort is used only as a test/benchmark baseline.'),
    ('Vector storage', 'Fixed array, raw new[]/delete[]', 'Dynamic size and straightforward ownership with standard C++.'),
    ('Unicode code-point counts', 'Byte counts, grapheme-cluster counts', 'Handles Ukrainian UTF-8 letters without external libraries; code-point scope is documented.'),
    ('Ordered map', 'Fixed byte table, unordered_map', 'Works for the Unicode range and produces deterministically ordered report rows.'),
    ('Text files', 'Binary formats, database, JSON library', 'Readable examples and results, with no extra runtime dependency.'),
], [107, 160, 201])
p('A fixed array of 256 counters would be sufficient for byte statistics, but '
  'would not directly represent Unicode characters. A map of char32_t keys '
  'makes the chosen interpretation visible in the source. A grapheme-aware '
  'application would need additional Unicode processing beyond this task.')
new()

h('3 Selected methods and algorithms')
h('3.1 Merge sort and operation counts', 2)
p('mergeRange works on a half-open interval [begin, end). A range with fewer '
  'than two elements is already ordered. Otherwise, the midpoint divides it '
  'into two ranges, both are sorted recursively, and their values are merged '
  'into the shared buffer before being copied back.')
p('The merge phase compares the next value from each half. The smaller value '
  'is appended to the buffer, and its source position advances. Equal values '
  'are taken from the left half first. When one half ends, the remaining values '
  'of the other half are appended without further element comparisons.')
terminal('mergeSort(values):\n  validate finite values and allocate buffer\n  mergeRange(0, N)\n\nmergeRange(begin, end):\n  if end - begin < 2: return\n  middle = begin + (end - begin) / 2\n  mergeRange(begin, middle)\n  mergeRange(middle, end)\n  merge the two ranges into buffer\n  copy buffer[begin:end] back to values')
p('At each recursive level the total merging work is proportional to N. The '
  'number of levels grows with log2(N), giving O(N log N) time. The auxiliary '
  'buffer uses O(N) storage and the recursion stack uses O(log N). The application '
  'also keeps the original array and a sorted copy so both outputs can be saved.')
p('An optional Metrics structure records element comparisons and assignment '
  'writes. One comparison is counted whenever the merge evaluates the two '
  'current values. The write count includes appending every merged value to '
  'the buffer and copying it back. It does not count input reading or vector '
  'initialisation. Benchmark timing uses a separate uninstrumented call.')
p('Appendix A includes the program workflow and recursive merge-sort flowchart. '
  'Tests compare results with an independent standard-library oracle and check '
  'the expected comparison bound. Signed zero provides a direct check that '
  'equal-valued elements retain their original order.')
new()

h('3.2 Character decoding and frequency counting', 2)
p('The text input is one UTF-8 line. An optional leading UTF-8 BOM and one '
  'terminal LF or CRLF are treated as file-format markers and removed. Empty '
  'input and extra lines are rejected. A string containing only spaces is '
  'valid because spaces are characters to be counted.')
p('The counter scans encoded bytes from left to right. The leading byte '
  'determines the sequence length. Continuation bytes are checked and assembled '
  'into a char32_t value. Overlong sequences, incomplete sequences, surrogate '
  'values and values beyond U+10FFFF are rejected according to UTF-8 validity '
  'constraints [5]. A valid value increments its map entry.')
terminal('readString(file)\nremove optional BOM and final LF/CRLF\nreject empty or multiline input\n\nfor each encoded sequence:\n  decode and validate one Unicode code point\n  frequencies[code_point] += 1\n\nfor each map entry in code-point order:\n  write code point, character label and count')
p('If the string contains C code points and K distinct values, map-based '
  'counting takes O(C log K) time, with decoding proportional to the byte '
  'length. The map uses O(K) additional space. Every reported count is positive '
  'because entries are created only for values actually encountered.')
p('The report distinguishes uppercase and lowercase letters. It performs '
  'neither Unicode normalisation nor case folding. A precomposed accented '
  'letter and a letter followed by a combining accent therefore produce '
  'different code-point records. That is an intentional boundary of this '
  'implementation, not a claim about visible user-perceived characters.')
p('Whitespace is labelled so its row remains readable. SPACE and TAB identify '
  'common cases; other controls use CONTROL with a separate U+ code-point '
  'column. Printable characters are written in UTF-8. Appendix B shows the '
  'decoding/counting loop and error exit.')
new()

h('4 Program development')
h('4.1 Source structure and data flow', 2)
table(['File', 'Responsibility'], [
    ('src/common.hpp', 'Shared prompt, bounded file reading, path checks and checked output writing.'),
    ('src/merge_sort.hpp', 'Count/real parsing, numeric file loading, merge sort, operation metrics and precise output formatting.'),
    ('src/merge_sort.cpp', 'Task 1 main function, keyboard/file selection, two output files and console preview.'),
    ('src/character_frequency.hpp', 'Single-line input, UTF-8 decoding, frequency table and report formatting.'),
    ('src/character_frequency.cpp', 'Task 2 main function, filenames, processing and completion/error messages.'),
    ('tests/core_tests.cpp', 'Direct checks of algorithms, parsing, numeric round trips and encoding boundaries.'),
    ('tests/cli_tests.py', 'Compiled-program tests and independent checks of saved outputs.'),
    ('benchmarks/benchmark.cpp', 'Repeatable timing experiment, correctness checks, CSV output and comparison counts.'),
], [161, 307])
p('Each application has its own main function and is built separately. The '
  'small headers keep functions available to the application, direct tests '
  'and benchmark without copying the algorithm into another implementation. '
  'Header guards prevent duplicate declarations within a translation unit.')
p('Task 1 data flows from keyboard or numeric file to the original vector, '
  'then to a copied vector for sorting. The two vectors are formatted and '
  'saved separately. Task 2 data flows from a bounded byte string to a Unicode '
  'frequency map and finally to a UTF-8 tab-separated report.')
new()

h('4.2 Validation, files and build environment', 2)
p('Numeric file loading reads N and requires exactly N tokens. A value must '
  'be a finite decimal number representable as double. The parser accepts '
  'scientific notation and rejects trailing text, infinities and NaN. The '
  'count must be a nonnegative integer within the supported range. Numeric '
  'files are limited to 64 MiB, which is sufficient for the supported arrays.')
p('Output uses max_digits10 precision so a saved double can be restored '
  'without a numeric change. Tests include the largest finite values, the '
  'smallest positive subnormal, signed zero and a repeating binary fraction. '
  'The console preview is rounded by its normal display formatting; the '
  'saved numeric file retains the full stored precision.')
p('Before writing, the programs check that output folders exist, output '
  'paths refer to regular files when present, and an output does not alias '
  'the input. Task 1 also rejects two output paths that refer to the same '
  'file. File streams are checked when opened and after being closed.')
p('Existing output files are overwritten. The writes are not transactional. '
  'A failure during writing can leave a partial output, and Task 1 may have '
  'saved the original before a later sorted-output write fails. Its success '
  'message for the original is printed immediately after that write; an '
  'error then identifies a failed later step. The report makes no guarantee '
  'against power loss or concurrent writers.')
p('All eight executable builds completed with Zig 0.17.1 using C++17 and '
  '-Wall -Wextra -Wpedantic -Werror -O2. Targets were Windows x86-64 and '
  'Linux x86-64. Full execution tests used Linux WSL. Native Windows '
  'Application Control blocked the sorter and test executable, so full '
  'Windows runtime verification remains uncompleted. The character '
  'program help command ran natively. No protection settings were changed.')
p('README.md provides direct compiler commands and an optional CMake route. '
  'No third-party C++ library is needed. Python is optional for console tests '
  'and report rebuilding. The alternative GCC, Microsoft cl and CMake '
  'commands are instructions, not claims that those tools were used in '
  'the recorded compilation.')
new()

h('5 Task 1: implementation, interface and testing')
h('5.1 Running the merge-sort program', 2)
p('Without arguments the application asks whether input comes from the '
  'keyboard or a file. Keyboard mode reads N on its own line and then '
  'accepts values separated by spaces or newlines. File mode asks for a '
  'filename. Both modes then ask for original and sorted output filenames, '
  'with original_array.txt and sorted_array.txt as defaults.')
terminal('merge_sort --file examples/numbers.txt original_array.txt sorted_array.txt\n\nInput file:\n8\n3.5 -2 0 3.5 10 -7.25 1.125 4')
terminal(compact_demo('Merge sort example'),
         'Figure 5.1 - Actual merge-sort output; only the machine-specific directory prefix is shortened.')
p('The full original and sorted files are included in examples/results/. '
  'The result is ascending, retains both occurrences of 3.5 and leaves the '
  'original input file unchanged. The console shows at most 20 sorted '
  'values for large inputs, while the output file stores all N values.')
p('An invalid selection, missing value, nonnumeric token or inaccessible '
  'file cancels the current run with an error and a nonzero exit status. '
  'End-of-input during prompts also cancels. The application performs '
  'one sorting operation per run rather than presenting a repeating menu.')
new()

h('5.2 Sorting test cases and observed results', 2)
table(['Case group', 'Expected and observed behaviour'], [
    ('Normal values and duplicates', 'Ascending result, exact original sequence in its own file, duplicate values retained.'),
    ('Empty, one element, ordered and reversed', 'Valid output for each arrangement, including N=0.'),
    ('Equal values and signed zero', 'Values remain ordered stably; signed-zero order is retained.'),
    ('Extreme finite values', 'Maximum, minimum, subnormal and high-precision values survive file round trips.'),
    ('Bad input', 'Negative/noninteger/oversized N, missing or extra tokens, NaN, infinity and numeric suffixes are rejected.'),
    ('Files and prompts', 'Missing files, conflicting paths, missing output folders and incomplete input produce errors.'),
    ('Independent comparison', '400 direct array sizes match std::stable_sort; console results are checked using Python sorted.'),
], [157, 311])
p('The direct suite also checks operation counts for a two-element case '
  'and comparison-count upper bounds across the tested sizes. The console '
  'suite reads the files actually written by the executable and verifies '
  'the count header and every value. Original outputs are checked with '
  'binary double comparisons so signed zero and precision are retained.')
terminal('Observed suite results in local Linux WSL:\nPASS: 992 core checks.\nPASS: 68 end-to-end cases.',
         'Figure 5.2 - Combined verification totals for both applications.')
p('All recorded cases passed. The console test register appears in '
  'Appendix D. The machine-readable records include source hashes, '
  'case names and selected captured sessions. They distinguish executed '
  'Linux results from the compiled but incompletely verified Windows binaries.')
new()

h('5.3 Timing experiment methodology', 2)
p('The experiment runs the same mergeSort function used by the application. '
  'std::sort is a practical standard-library baseline. It is not used '
  'inside the application implementation. Each timing result is an elapsed '
  'interval measured with steady_clock, a monotonic clock appropriate for '
  'duration measurement [6].')
table(['Parameter', 'Recorded configuration'], [
    ('Environment', 'Intel Core i7-11800H, 8 cores / 16 logical processors; local Linux WSL x86-64, kernel 6.18.33.2-microsoft-standard-WSL2.'),
    ('Compiler', 'Zig 0.17.1 with libc++, C++17, -O2 and strict warning checks.'),
    ('Array sizes', '100; 1,000; 10,000; 100,000; 1,000,000.'),
    ('Input patterns', 'Random, sorted, reverse-sorted and few_unique (eight distinct numeric values).'),
    ('Repeatability', 'mt19937 seed 20261121 plus N; one deterministic dataset per pattern/size.'),
    ('Repetitions', 'One warm-up batch per algorithm, then nine measured repetitions with alternating algorithm order.'),
    ('Small-input batches', '128, 32, 4, 1 and 1 sorts per measured batch for the five sizes respectively.'),
    ('Recorded measures', 'Microseconds per sort, median, Q1, Q3, minimum, maximum and separately measured comparison counts.'),
], [124, 344])
p('Inputs are copied before the timer starts. The timed region contains '
  'the calls that perform the sort. The merge-sort call includes its '
  'finite-value check and scratch-buffer allocation. Both the baseline '
  'and merge-sort outputs are compared with the expected result after '
  'the timer stops. Input generation, file access, expected-result '
  'construction and comparison-count passes are excluded.')
new()

h('5.4 Measured timing results', 2)
picture('timing.png', 468, 358,
        'Figure 5.3 - Median time per sort; shaded ranges show Q1-Q3 over nine repetitions. Both axes are logarithmic.')
p('The raw CSV contains 360 timed batches and the summary contains 40 '
  'algorithm/pattern/size rows. Every timed result passed its correctness '
  'check. An independent Python check recomputed the summary statistics '
  'from the raw observations.')
table(['N, random input', 'Merge median, ms', 'std::sort median, ms', 'Merge Q1-Q3, ms'], [
    (f'{n:,}', f"{float(row('random', n, 'merge_sort')['median_us']) / 1000:.5f}",
     f"{float(row('random', n, 'std_sort')['median_us']) / 1000:.5f}",
     f"{float(row('random', n, 'merge_sort')['q1_us']) / 1000:.5f} - {float(row('random', n, 'merge_sort')['q3_us']) / 1000:.5f}")
    for n in META['sizes']], [102, 112, 119, 135])
new()

h('5.5 Comparison counts and interpretation', 2)
picture('comparisons.png', 468, 234,
        'Figure 5.4 - Element-comparison counts on random input, with N log2(N) as a growth reference.')
table(['N', 'Merge comparisons', 'std::sort comparisons', 'Merge / N log2(N)'], [
    (f'{n:,}', f"{int(row('random', n, 'merge_sort')['comparisons']):,}",
     f"{int(row('random', n, 'std_sort')['comparisons']):,}",
     f"{int(row('random', n, 'merge_sort')['comparisons']) / (n * math.log2(n)):.3f}")
    for n in META['sizes']], [89, 124, 134, 121])
random_merge = float(row('random', 1000000, 'merge_sort')['median_us']) / 1000
random_std = float(row('random', 1000000, 'std_sort')['median_us']) / 1000
p(f'For 1,000,000 random elements, the merge-sort median was {random_merge:.3f} ms '
  f'and the std::sort median was {random_std:.3f} ms. Merge sort used fewer '
  'element comparisons on this random dataset but took longer. Comparisons '
  'alone do not measure all the work: buffer allocation, validation, '
  'assignment traffic, branching and library optimisation also affect time.')
p('The random comparison counts grow in the expected N log N range. '
  'That observation supports the implementation analysis but is not an '
  'experimental proof of the asymptotic bound. The theoretical bound '
  'comes from the recursive split and linear merge work.')
new()

h('5.6 Input patterns and measurement limits', 2)
table(['Pattern, N=1,000,000', 'Merge median, ms', 'std::sort median, ms', 'Time ratio'], [
    (pattern.replace('_', ' '),
     f"{float(row(pattern, 1000000, 'merge_sort')['median_us']) / 1000:.3f}",
     f"{float(row(pattern, 1000000, 'std_sort')['median_us']) / 1000:.3f}",
     f"{float(row(pattern, 1000000, 'merge_sort')['median_us']) / float(row(pattern, 1000000, 'std_sort')['median_us']):.2f}")
    for pattern in META['patterns']], [147, 114, 126, 81])
p('The baseline was faster for all recorded configurations in this run. '
  'Its advantage was especially large on sorted and reverse-sorted input. '
  'The teaching implementation always recursively sorts both halves and '
  'copies merged values back, even when the original array is already '
  'ordered. No early-exit or small-array insertion-sort optimisation is used.')
p('The two sort calls do not perform identical internal work. Merge sort '
  'validates its input and allocates a buffer, while the baseline call '
  'receives the known-finite values directly. The purpose is to compare '
  'these callable implementations under a stated procedure, not to '
  'attribute the difference solely to an abstract algorithm.')
p('The experiment uses one deterministic dataset for each pattern and '
  'size. Repetitions measure run-to-run timing variation on that dataset. '
  'They are not independent samples of every possible input distribution. '
  'The Q1-Q3 bands describe the observed timing spread and are not '
  'confidence intervals for general relative performance.')
p('The machine was not isolated from background activity, CPU scheduling, '
  'cache behaviour or power-management effects. The measurements were '
  'made in WSL with this compiler and library. Native Windows timings '
  'were not collected. Re-running the same benchmark can produce '
  'different durations while retaining the deterministic input values '
  'and comparison counts.')
p('The benchmark source, raw samples, summary and environment metadata '
  'are included. Appendix E lists the medians and counts for all 20 '
  'pattern/size configurations. All output arrays were checked after '
  'timing so the measured work could not be accepted with an incorrect result.')
new()

h('6 Task 2: implementation, interface and testing')
h('6.1 Running the character-frequency program', 2)
p('The application accepts an input filename and a report filename as '
  'arguments. Without arguments, it prompts for those names, with '
  'input.txt and report.txt as defaults. The input must be one valid '
  'UTF-8 line; a final line ending is optional.')
terminal('character_frequency examples/input.txt report.txt\n\nInput text:\nHello, world! Hello!')
terminal(compact_demo('English character example'),
         'Figure 6.1 - Actual completion output for the English example, with the directory prefix shortened.')
terminal((ROOT / 'examples' / 'results' / 'english_report.txt').read_text(encoding='utf-8'))
p('The input contains 20 code points and 10 distinct values. For '
  'example, uppercase H occurs twice, lowercase l occurs five times '
  'and SPACE occurs twice. The report contains one row for each '
  'distinct value; absent characters are not given zero-count rows.')
new()

h('6.2 Unicode input and report behaviour', 2)
terminal('Input text:\nПривіт, світе! Привіт!')
terminal(compact_demo('Ukrainian character example'),
         'Figure 6.2 - Actual completion output for Ukrainian UTF-8 input, with the directory prefix shortened.')
table(['Code point', 'Character', 'Count'], [
    record.split('\t') for record in
    (ROOT / 'examples' / 'results' / 'ukrainian_report.txt').read_text(encoding='utf-8').splitlines()[1:]
], [137, 194, 137])
p('The program counts Ukrainian letters as code points. It does not '
  'require a Ukrainian locale for counting; the decoder processes '
  'UTF-8 directly. The appearance of those characters on a terminal '
  'still depends on the terminal encoding and available font. The '
  'saved report is UTF-8 regardless of console rendering.')
p('The same approach supports valid four-byte code points. This '
  'extends the simple char-based example while keeping the program '
  'within the standard library. It does not add case-insensitive '
  'analysis, word counting or Unicode grapheme segmentation.')
new()

h('6.3 Character test cases and observed results', 2)
table(['Case group', 'Expected and observed behaviour'], [
    ('Repetitions and unique text', 'Correct counts for repeated letters and one report row for each of ten different characters.'),
    ('Whitespace and punctuation', 'Spaces, tabs, punctuation and case distinctions are preserved.'),
    ('Unicode', 'Ukrainian, four-byte characters, combining code points and boundary scalar values are counted correctly.'),
    ('File markers', 'A leading BOM and final LF/CRLF are excluded. Additional lines are rejected.'),
    ('Malformed input', 'Empty files, malformed UTF-8, truncated sequences, surrogates and out-of-range code points are rejected.'),
    ('Limits and file paths', 'The 4 MiB boundary is tested. Missing inputs, input/output aliasing and invalid output folders produce errors.'),
    ('Independent checks', 'Direct expected maps and Python Counter are compared with the actual UTF-8 report rows.'),
], [145, 323])
p('The direct suite includes 100 generated valid Unicode sequences '
  'with known frequency maps. It also exercises UTF-8 encoding-length '
  'boundaries and malformed sequences. Console tests read and parse '
  'the file generated by the executable, verifying positive counts, '
  'unique rows and ascending code-point order.')
session = TESTS['console_sessions']['Reject invalid text file 4']
terminal(session['stderr'].strip(), 'Figure 6.3 - Actual error when the input file contains a second line.')
p('All recorded character cases passed as part of the 992 core '
  'checks and 68 end-to-end cases. Invalid input was rejected '
  'before a report file was written, and the input bytes were '
  'checked to confirm that they remained unchanged.')
new()

h('Conclusions')
p('The two practice tasks have been implemented as separate C++17 '
  'console applications. The sorting program performs recursive '
  'merge sort on dynamically allocated real-number arrays, supports '
  'keyboard and file input, and saves both original and sorted '
  'data. The character program reads a file-based string and '
  'writes one count for every distinct Unicode code point.')
p('The source separates input handling, processing and formatting. '
  'The numeric program checks declared counts and finite values, '
  'preserves precise output values and handles empty arrays. The '
  'text program defines single-line UTF-8 input, includes whitespace '
  'and punctuation, and reports encoding and file errors.')
p('Compilation passed for all Windows and Linux application, test '
  'and benchmark targets. Full Linux execution passed 992 direct '
  'checks and 68 end-to-end cases. The native Windows runtime '
  'limitation is documented rather than represented as a passing '
  'test. Demonstration files and machine-readable evidence accompany '
  'the report.')
p('The timing study produced 360 measured batches across five '
  'sizes, four patterns and two implementations. The observed '
  'comparison counts follow the expected merge-sort growth. '
  'The standard-library baseline was faster in the recorded '
  'configurations, even when merge sort used fewer element '
  'comparisons on random input. The result illustrates the '
  'difference between a comparison count and total execution work.')
p('Possible improvements include a hybrid small-array strategy, '
  'skipping merges when adjacent ranges are already ordered, '
  'transactional output replacement and richer Unicode text '
  'segmentation. Those features are outside this version. The '
  'current result provides the required algorithms, tests, '
  'performance experiment and supporting documentation for review.')
new()

h('References')
references = [
    ('UzhNU Moodle. Programming, part 2. Task for Practice and attached Task.pdf.',
     'https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=74000'),
    ('UzhNU Moodle. Practice example.pdf. Report structure, example applications and appendices.',
     'https://moodle.uzhnu.edu.ua/pluginfile.php/131919/mod_assign/introattachment/0/Practice%20example.pdf'),
    ('Sedgewick, R.; Wayne, K. Algorithms, 4th edition. Section 2.2, Mergesort. Princeton University.',
     'https://algs4.cs.princeton.edu/22mergesort/'),
    ('Microsoft Learn. C++ Standard Library: vector class.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/vector-class'),
    ('The Unicode Consortium. The Unicode Standard, Version 17.0. Chapter 3, Conformance; UTF-8 encoding form.',
     'https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-3/'),
    ('Microsoft Learn. C++ Standard Library: steady_clock structure.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/steady-clock-struct'),
]
for number, (description, url) in enumerate(references, 1):
    p(f'[{number}] {escape(description)}<br/><link href="{escape(url)}" color="#165587">'
      f'{escape(url)}</link><br/>Accessed 21 November 2026.', 'Small')
p('Local verification sources are docs/test_results.json, '
  'docs/demo_sessions.json, benchmarks/linux_raw.csv, '
  'benchmarks/linux_summary.csv and benchmarks/metadata.json. '
  'They contain the case register, captured output, measurements '
  'and source hashes for the version described here.', 'Small')
new()

h('Appendix A. Merge-sort flowcharts')
story.append(Flowchart('sort_program'))
p('Figure A.1 - Task 1 program flow. Exceptions from input, path checks, sorting or writing print an error and end the run.', 'Caption')
p('The sorted result is created on a copy, so the original values remain '
  'available for saving. Original and sorted files are written in that '
  'order. The program does not repeat its menu after an error.', 'Small')
new()
p('Recursive sorting and merging', 'File')
story.append(Flowchart('merge'))
p('Figure A.2 - Recursive split, stable merge and copy-back for a half-open range.', 'Caption')
p('The first comparison chooses the left value on equality. Remaining '
  'values are appended when one half is exhausted. One shared buffer '
  'is reused by every recursive call.', 'Small')
new()

h('Appendix B. Character-analysis flowchart')
story.append(Flowchart('characters'))
p('Figure B.1 - File loading, UTF-8 decoding, counting and report writing.', 'Caption')
p('File read errors, empty/multiline input and output errors also use '
  'the error exit. A failed decode never reaches the report-writing '
  'step. Optional file markers are removed before counting.', 'Small')
new()

h('Appendix C. Complete application and benchmark source')
p('The listing contains every application source/header file and the '
  'benchmark runner. Printed line numbers are reference aids and '
  'are not present in the compilable files. Long lines wrap only '
  'in this document.', 'Small')
for relative in ['src/common.hpp', 'src/merge_sort.hpp', 'src/merge_sort.cpp',
                 'src/character_frequency.hpp', 'src/character_frequency.cpp', 'benchmarks/benchmark.cpp']:
    p(relative, 'File')
    lines = []
    for number, line in enumerate((ROOT / relative).read_text(encoding='utf-8').splitlines(), 1):
        wrapped = textwrap.wrap(line, width=104, replace_whitespace=False, drop_whitespace=False) or ['']
        lines.append(f'{number:3}  ' + wrapped[0])
        lines.extend('     ' + item for item in wrapped[1:])
    for start in range(0, len(lines), 45):
        story.append(Preformatted('\n'.join(lines[start:start + 45]), styles['Code']))
    story.append(Spacer(1, 10))
new()

h('Appendix D. End-to-end test register')
p('All 68 cases below passed against the compiled Linux executables '
  'in local WSL. They supplement the 992 direct C++ checks. '
  'The actual executable and result files were tested; no '
  'screen-only success check was used. Literal \\n and \\r below denote file line endings.', 'Small')
array_details = [
    'empty file', 'N=-1', 'N=1.5', 'N=1000001', 'N=3 with only 1 and 2',
    'N=2 with 1, 2 and 3', 'NaN value', 'infinite value', 'overflowing 1e999',
    'value 3x', 'N=0 with trailing data', 'nonnumeric token two',
]
text_details = [
    'empty file', 'LF only', 'CRLF only', 'first\\nsecond', 'first\\n\\n',
    'byte FF', 'overlong C0 AF', 'surrogate ED A0 80', 'out-of-range F4 90 80 80',
    'truncated F0 9F 98', 'more than 4 MiB',
]


def test_description(item):
    name = item['name']
    for prefix, details in [('Reject invalid array file ', array_details), ('Reject invalid text file ', text_details)]:
        if name.startswith(prefix):
            return name + ': ' + details[int(name[len(prefix):]) - 1]
    return name


table(['No.', 'Program', 'Case', 'Result'], [
    (number, 'Sort' if item['program'] == 'merge_sort' else 'Characters', test_description(item), 'Pass')
    for number, item in enumerate(TESTS['results'], 1)
], [30, 71, 325, 42])
new()

h('Appendix E. Benchmark summary')
p('Medians are microseconds per sort from nine measured repetitions. '
  'Counts are element comparisons from a separate untimed pass. '
  'M means the implemented merge sort; S means std::sort. '
  'Full quartiles, minima and maxima are retained in the summary '
  'CSV, with all samples in the raw CSV.', 'Small')
table(['Pattern', 'N', 'M time, us', 'S time, us', 'M compares', 'S compares'], [
    (pattern.replace('_', ' '), f'{n:,}',
     f"{float(row(pattern, n, 'merge_sort')['median_us']):.3f}",
     f"{float(row(pattern, n, 'std_sort')['median_us']):.3f}",
     f"{int(row(pattern, n, 'merge_sort')['comparisons']):,}",
     f"{int(row(pattern, n, 'std_sort')['comparisons']):,}")
    for pattern in META['patterns'] for n in META['sizes']
], [83, 65, 78, 78, 82, 82])


if __name__ == '__main__':
    make_plots()
    destination = DOCS / 'Practice_Report.pdf'
    document = Report(str(destination), pagesize=A4, leftMargin=25 * mm, rightMargin=20 * mm,
                      topMargin=22 * mm, bottomMargin=20 * mm,
                      title='Programming Training Practice - Merge Sort and Character Frequency',
                      author='Кортні Шілдс Скаллі')
    frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height,
                  id='body', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    document.addPageTemplates(PageTemplate(id='report', frames=frame, onPage=decorate))
    document.multiBuild(story)
    print(f'Created {destination}')
