# Naïve Wordlist Generator (Python)

**Generates every possible string** of a fixed length from a given character set and writes them to `wordlist.txt`.

## How It Works
- Character sets: lowercase, uppercase, digits, and a set of special characters.
- Parameters: `min_length` and `max_length` (currently both 12).
- Uses `itertools.product(charset, repeat=length)` to enumerate all combinations and writes each line.

## Requirements
Python 3.8+ (standard library only).

## Usage (WARNING)
```bash
python crunchmimic.py
```
> ⚠️ **Combinatorial Explosion:** With the default set (~88 characters) and length 12, the search space is **astronomically large** (|Σ|^12). This is computationally infeasible (time, disk) on any normal system.

## Practical Considerations
- This code is educational: it demonstrates Cartesian‑product generation but is **not** practical for real wordlists at large lengths.
- If you need realistic testing data, prefer **constrained generation** (smaller charsets, short lengths) or sample‑based approaches.
- **Ethics & Legality:** Only generate or use wordlists for **authorized** security testing on systems you own or have explicit permission to test.

## Safer Defaults
- Reduce `max_length` dramatically (e.g., 3–5) or shrink the character set before running.
- Stream to stdout or chunk output to avoid filling disks.

## License
Add your preferred license.
