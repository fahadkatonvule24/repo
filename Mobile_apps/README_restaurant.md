# Restaurant Menu CLI (Kotlin/JVM)

A tiny console menu taking user input and printing confirmations + totals for selected items across Main Course, Snacks, and Drinks.

## Features
- Intro screen and a main selector (1: Main course, 2: Snacks, 3: Drinks)
- Item pickers with simple pricing and quantity prompts for Snacks/Drinks
- Prints an order confirmation and computed total

## Build & Run

```bash
kotlinc restaurant.kt -include-runtime -d restaurant.jar
java -jar restaurant.jar
```

## Notes & Improvements
- **Validation**: Add error handling for non‑integer input and negative quantities.
- **Currency consistency**: Drink totals currently use `1600`/`800` vs menu showing `16000`/`8000`. Align as intended.
- **Separation of concerns**: Consider data classes for menu items and a small pricing engine to avoid repetition.
- **Testing**: Extract pure functions for totals and write unit tests.
- **i18n/UI**: If evolving beyond a console, separate UI strings and add localization.

## License
Add your preferred license.
