import re
import string

def password_strength(password):
    """
    Evaluates password strength based on:
    - Length (minimum 8 characters)
    - Character variety (uppercase, lowercase, digits, special characters)
    - Complexity (patterns and character distribution)
    Returns: Weak, Medium, Strong, or Very Strong
    """
    # Check for minimum length
    if len(password) < 8:
        return "Weak (Too short)"
    
    # Check for common weak passwords
    common_passwords = input ("Enter a comma-separated list of common passwords: ").split(',')
    common_passwords = [pwd.strip().lower() for pwd in common_passwords]
    if password.lower() in common_passwords:
        return "Weak (Common password)"

    # Initialize strength flags
    has_upper = False
    has_lower = False
    has_digit = False
    has_special = False
    unique_chars = set()

    # Character type analysis
    for char in password:
        unique_chars.add(char)
        if char in string.ascii_uppercase:
            has_upper = True
        elif char in string.ascii_lowercase:
            has_lower = True
        elif char in string.digits:
            has_digit = True
        else:
            has_special = True

    # Character variety score
    type_score = sum([has_upper, has_lower, has_digit, has_special])
    
    # Check for character repetition and sequences
    has_repetition = bool(re.search(r'(.)\1{2,}', password))  # 3+ repeating chars
    has_sequence = bool(
        re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz|012|123|234|345|456|567|678|789)', password.lower())
    )

    # Evaluate strength
    length = len(password)
    uniqueness = len(unique_chars) / len(password)  # Character diversity ratio
    
    # Scoring system
    score = 0
    
    # Length scoring
    if length >= 12:
        score += 2
    elif length >= 8:
        score += 1
        
    # Character variety scoring
    if type_score == 4:
        score += 3
    elif type_score == 3:
        score += 2
    elif type_score == 2:
        score += 1
        
    # Deductions for weaknesses
    if has_repetition:
        score -= 1
    if has_sequence:
        score -= 1
    if uniqueness < 0.6:  # Low character diversity
        score -= 1

    # Final evaluation
    if score >= 4:
        return "Very Strong"
    elif score >= 3:
        return "Strong"
    elif score >= 2:
        return "Medium"
    else:
        return "Weak"

# Test the function
if __name__ == "__main__":
    test_passwords = [
        "short", 
        "password", 
        "abc123", 
        "Hello123", 
        "SecureP@ss1", 
        "VeryL0ngP@$$w0rdWithVariety!"
    ]
    
    for pwd in test_passwords:
        print(f"'{pwd}': {password_strength(pwd)}")