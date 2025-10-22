# NIRA Console Simulation (Kotlin/JVM)

A console‑based prototype simulating a National Identity & Registration workflow: user registration with phone verification, biometric login toggling, password management, admin portal (logs, unblock accounts), and activity logging.

## Features
- **Registration** with NIN (14 digits), phone verification via simulated SMS code
- **Login** with password or (optional) simulated biometrics
- **Account ops**: renew ID, report lost ID, view activity log, change password, toggle biometrics
- **Admin portal**: view system logs, unblock accounts, inspect user details
- **Basic rate‑limiting**: failed login attempts → temporary block

## Build & Run

Using Kotlin CLI:

```bash
kotlinc nira.kt -include-runtime -d nira.jar
java -jar nira.jar
```

Or with Gradle Kotlin/JVM, include `application` plugin and set `mainClass` accordingly.

## Architecture
- `User` class
  - Phone number stored encrypted (AES/ECB/PKCS5Padding) in memory
  - Password stored as SHA‑256 hash (string hex)
  - Activity log capped at 20 entries
- `Home` class
  - Menus, flows, simulated SMS codes, biometric prompts, admin tools
  - In‑memory `registeredUsers`, `failedAttempts`, `blockedUsers`, `systemLog`

## Security Review (Important)
- **AES‑ECB** is **not secure** for real systems (pattern leakage, no IV). Prefer **AES‑GCM** or **AES‑CBC + HMAC**, with random IVs and a **non‑hardcoded key** loaded from secure storage or a KMS.
- **Hardcoded key** (`NIRA_System_Secret`) should be removed. Use environment configs/secret managers.
- **Password hashing**: SHA‑256 without salt/iterations is weak against offline attacks. Use **Argon2**, **bcrypt**, or **PBKDF2** with a per‑user salt.
- **Admin password** is compared using `hashCode()` of a string, which is not cryptographic. Replace with the same strong KDF as above and constant‑time comparison.
- **Biometrics** here are simulated. Real implementations must use platform APIs (e.g., AndroidX Biometric) and NEVER expose biometric secrets.

## Limitations
- In‑memory state only (no database). Data is lost on exit.
- Console I/O via `readln()` is synchronous and not validated against malformed input beyond length.
- Demo‑only; not for production use.

## License
Add your preferred license.
