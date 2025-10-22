# Password Strength Tester (Python)

Evaluates the strength of a password using length, character‑type variety, diversity, and penalties for repetition and sequences. Returns one of: **Weak**, **Medium**, **Strong**, **Very Strong**.

## How It Works
- Enforces minimum length (8).
- Checks against a user‑provided list of common passwords (entered interactively).
- Scores presence of uppercase, lowercase, digits, special characters.
- Penalizes obvious sequences and repeated characters.
- Computes a final score mapped to an overall rating.

## Requirements
Python 3.8+ (standard library only).

## Usage

```bash
python pswdtester.py
```

You’ll be prompted for a comma‑separated list of common passwords (e.g., `password, 123456, qwerty`). The script then evaluates the test cases in `__main__` or can be imported and `password_strength()` called directly.

## Notes & Suggestions
- **Interactive dependency**: The function currently **prompts for input** every call to get the common password list. For reuse/imports, refactor to accept an argument like `common_list=None` rather than calling `input()` inside the function.
- **Wordlists**: Maintain external lists (e.g., a file) and load once rather than per call.
- **Entropy**: Consider adding an entropy estimate for more granular scoring.
- **Testing**: Add unit tests for edge cases (e.g., all same char, unicode, very long strings).

## License
Add your preferred license.
