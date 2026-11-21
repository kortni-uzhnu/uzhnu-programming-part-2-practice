"""Test the compiled practice programs using Python's standard library."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bin-dir', type=Path, default=ROOT / 'build')
parser.add_argument('--suffix', default='.exe' if __import__('os').name == 'nt' else '')
parser.add_argument('--wsl', help='Optional local WSL distribution for a Linux build')
parser.add_argument('--results', type=Path)
options = parser.parse_args()
results = []
sessions = {}


def path_for_program(path):
    path = Path(path).resolve()
    return '/mnt/host/' + path.drive[0].lower() + path.as_posix()[2:] if options.wsl else str(path)


def run(program, name, directory, arguments=(), text='', expected_code=0, contains=(), error='', capture=False):
    command = [path_for_program(options.bin_dir / (program + options.suffix)), *arguments]
    if options.wsl:
        command = ['wsl', '-d', options.wsl, '--cd', path_for_program(directory), '--exec', *command]
    process = subprocess.run(command, input=text.encode('utf-8'), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, cwd=ROOT if options.wsl else directory, timeout=25)
    output = process.stdout.decode('utf-8')
    errors = process.stderr.decode('utf-8')
    assert process.returncode == expected_code, (name, process.returncode, output, errors)
    for fragment in contains:
        assert fragment in output, (name, fragment, output)
    if expected_code == 0:
        assert errors == '', (name, errors)
    else:
        assert 'Error:' in errors or 'Usage:' in errors or 'Usage:' in output, (name, output, errors)
        if error:
            assert error in errors, (name, error, errors)
    results.append({'program': program, 'name': name, 'status': 'PASS'})
    if capture:
        sessions[name] = {'stdin': text, 'stdout': output, 'stderr': errors}
    return output


def load_array(path):
    words = path.read_text(encoding='utf-8').split()
    count = int(words[0])
    assert len(words) == count + 1
    return [float(word) for word in words[1:]]


def identical_numbers(a, b):
    return len(a) == len(b) and all(struct.pack('!d', x) == struct.pack('!d', y) for x, y in zip(a, b))


def report_counts(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines[0] == 'Code point\tCharacter\tCount'
    counts = {}
    for line in lines[1:]:
        point, label, count = line.split('\t')
        character = chr(int(point[2:], 16))
        assert character not in counts
        assert int(count) > 0
        counts[character] = int(count)
    assert list(counts) == sorted(counts, key=ord)
    return counts


with tempfile.TemporaryDirectory(prefix='practice-cli-') as temporary:
    base = Path(temporary)
    next_case = 0

    def fresh():
        global next_case
        directory = base / f'case-{next_case:03}'
        next_case += 1
        directory.mkdir()
        return directory

    arrays = [
        ('Mixed real numbers and duplicates', [3.5, -2, 0, 3.5, 10, -7.25, 1.125, 4]),
        ('Empty array', []), ('Single element', [-4.75]),
        ('Already sorted', [-10, -2, 0, 3.5, 7]), ('Reverse sorted', [9, 7, 5, 3, 1]),
        ('All equal', [2.25] * 12), ('Signed zero stability', [0.0, -0.0, 0.0, -0.0]),
        ('Extreme finite values', [float.fromhex('0x1.fffffffffffffp1023'),
                                  -float.fromhex('0x1.fffffffffffffp1023'),
                                  float.fromhex('0x0.0000000000001p-1022'), 1e-300, 1e100]),
    ]
    rng = random.Random(20261121)
    arrays.append(('Seeded larger array', [rng.uniform(-1000, 1000) for _ in range(3000)]))
    for name, values in arrays:
        directory = fresh()
        source = directory / 'input numbers.txt'
        original = directory / 'original.txt'
        sorted_path = directory / 'sorted.txt'
        content = str(len(values)) + '\n' + ' '.join(repr(value) for value in values) + '\n'
        source.write_text(content, encoding='utf-8')
        run('merge_sort', name, directory,
            ['--file', path_for_program(source), path_for_program(original), path_for_program(sorted_path)],
            contains=['Original array saved', 'Sorted array saved', 'Element comparisons:'],
            capture=name == 'Mixed real numbers and duplicates')
        assert identical_numbers(load_array(original), values), name
        assert identical_numbers(load_array(sorted_path), sorted(values)), name
        assert source.read_text() == content
    directory = fresh()
    run('merge_sort', 'Interactive keyboard input', directory,
        text='1\n5\n4.5 -2\n7 0 4.5\n\n\n', contains=['Sorted array (5 elements):'], capture=True)
    assert load_array(directory / 'sorted_array.txt') == [-2, 0, 4.5, 4.5, 7]
    assert load_array(directory / 'original_array.txt') == [4.5, -2, 7, 0, 4.5]
    directory = fresh()
    (directory / 'numbers.txt').write_text('3\n3 -1 2\n')
    run('merge_sort', 'Interactive file input', directory,
        text='2\n' + path_for_program(directory / 'numbers.txt') + '\n' +
             path_for_program(directory / 'original.txt') + '\n' + path_for_program(directory / 'sorted.txt') + '\n',
        contains=['Sorted array (3 elements):'])
    assert load_array(directory / 'sorted.txt') == [-1, 2, 3]
    for index, content in enumerate(['', '-1\n', '1.5\n', '1000001\n', '3\n1 2\n', '2\n1 2 3\n',
                                     '1\nnan\n', '1\ninf\n', '1\n1e999\n', '1\n3x\n',
                                     '0\nextra\n', '3\n1 two 3\n']):
        directory = fresh()
        source = directory / 'bad.txt'
        source.write_text(content)
        run('merge_sort', f'Reject invalid array file {index + 1}', directory,
            ['--file', path_for_program(source), path_for_program(directory / 'original.txt'),
             path_for_program(directory / 'sorted.txt')], expected_code=1)
        assert not (directory / 'original.txt').exists() and not (directory / 'sorted.txt').exists()
        assert source.read_text() == content
    for name, text in [('Invalid menu', '3\n'), ('Non-numeric size', '1\nabc\n'),
                       ('Keyboard numeric suffix', '1\n1\n3x\n'), ('Extra keyboard values', '1\n1\n2 3\n'),
                       ('Interrupted keyboard entry', '1\n3\n1\n'), ('Interrupted output prompt', '1\n1\n2\n')]:
        directory = fresh()
        run('merge_sort', name, directory, text=text, expected_code=1, capture=name == 'Non-numeric size')
        assert not (directory / 'original_array.txt').exists()
    directory = fresh()
    input_path = directory / 'in.txt'
    input_path.write_text('3\n3 1 2\n')
    for name, source, outputs in [
        ('Missing numeric input file', directory / 'missing.txt', [directory / 'a.txt', directory / 'b.txt']),
        ('Protect numeric input file', input_path, [input_path, directory / 'b.txt']),
        ('Reject duplicate numeric outputs', input_path, [directory / 'a.txt', directory / '.' / 'a.txt']),
        ('Reject missing output folder', input_path, [directory / 'a.txt', directory / 'missing' / 'b.txt']),
        ('Reject directory as numeric output', input_path, [directory / 'a.txt', directory]),
    ]:
        run('merge_sort', name, directory, ['--file', path_for_program(source),
            *[path_for_program(path) for path in outputs]], expected_code=1)
        assert input_path.read_text() == '3\n3 1 2\n' and not (directory / 'a.txt').exists()
    run('merge_sort', 'Merge sort help', directory, ['--help'], contains=['Usage:'])
    run('merge_sort', 'Reject merge sort argument count', directory, ['one', 'two'], expected_code=1)

    texts = [
        ('Repeated ASCII letters', 'banana'), ('Ten distinct characters', 'abcdefghij'),
        ('Spaces punctuation and case', 'Aa a!\t!'), ('Spaces only', '   '),
        ('Ukrainian string', 'Привіт, світе! Привіт!'), ('Emoji characters', '😀😀🙂'),
        ('Combining characters', 'ée\u0301'), ('Control characters', '\0\t\r\x1b\x7f'),
        ('Unicode boundaries', '\x7f\x80\u07ff\u0800\ud7ff\ue000\uffff\U00010000\U0010ffff'),
        ('Printable ASCII alphabet', ''.join(chr(i) for i in range(32, 127))),
    ]
    for name, value in texts:
        directory = fresh()
        source = directory / 'input text.txt'
        output_path = directory / 'report.txt'
        source.write_bytes(value.encode('utf-8'))
        run('character_frequency', name, directory, [path_for_program(source), path_for_program(output_path)],
            contains=[f'Distinct characters: {len(Counter(value))}', f'Characters counted: {len(value)}'],
            capture=name in ['Repeated ASCII letters', 'Ukrainian string'])
        assert report_counts(output_path) == dict(Counter(value)), name
    for name, ending, bom in [('Final LF', b'\n', b''), ('Final CRLF', b'\r\n', b''),
                              ('Optional UTF-8 BOM', b'\r\n', b'\xef\xbb\xbf')]:
        directory = fresh()
        source = directory / 'input.txt'
        source.write_bytes(bom + b'aba' + ending)
        run('character_frequency', name, directory,
            [path_for_program(source), path_for_program(directory / 'report.txt')])
        assert report_counts(directory / 'report.txt') == {'a': 2, 'b': 1}
    for index, invalid in enumerate([b'', b'\n', b'\r\n', b'first\nsecond', b'first\n\n',
                                    b'\xff', b'\xc0\xaf', b'\xed\xa0\x80', b'\xf4\x90\x80\x80',
                                    b'\xf0\x9f\x98', b'A' * (4 * 1024 * 1024 + 6)]):
        directory = fresh()
        source = directory / 'invalid.txt'
        source.write_bytes(invalid)
        run('character_frequency', f'Reject invalid text file {index + 1}', directory,
            [path_for_program(source), path_for_program(directory / 'report.txt')], expected_code=1,
            capture=index == 3)
        assert not (directory / 'report.txt').exists()
        assert source.read_bytes() == invalid
    directory = fresh()
    source = directory / 'input.txt'
    source.write_bytes(b'aba')
    for name, input_path, output_path in [
        ('Missing text input file', directory / 'missing.txt', directory / 'out.txt'),
        ('Protect text input file', source, source),
        ('Missing text output folder', source, directory / 'missing' / 'out.txt'),
        ('Reject directory as text output', source, directory),
    ]:
        run('character_frequency', name, directory,
            [path_for_program(input_path), path_for_program(output_path)], expected_code=1)
        assert source.read_bytes() == b'aba'
    (directory / 'report.txt').write_text('old report')
    run('character_frequency', 'Replace an existing output report', directory,
        [path_for_program(source), path_for_program(directory / 'report.txt')])
    assert report_counts(directory / 'report.txt') == {'a': 2, 'b': 1}
    run('character_frequency', 'Interactive text filenames', directory,
        text=path_for_program(source) + '\n' + path_for_program(directory / 'interactive.txt') + '\n',
        contains=['Report saved to'])
    assert report_counts(directory / 'interactive.txt') == {'a': 2, 'b': 1}
    run('character_frequency', 'Character analysis help', directory, ['--help'], contains=['Usage:'])
    run('character_frequency', 'Reject character analysis argument count', directory, ['one'], expected_code=1)

summary = {
    'date': date(2026, 11, 21).isoformat(),
    'platform': 'Linux WSL' if options.wsl else 'Windows native',
    'execution_cases_passed': len(results), 'results': results, 'console_sessions': sessions,
    'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT / 'src').glob('*'))},
}
if options.results:
    options.results.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'PASS: {len(results)} end-to-end cases.')
