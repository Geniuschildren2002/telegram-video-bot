# Structure

`index.html` is a self-contained browser game. CSS defines the responsive command-console UI; the `<canvas>` renders the battlefield, fortress, road, and enemies; the inline JavaScript owns game state, wave spawning, enemy motion, combat ticks, upgrades, hero cooldown, rewards, and UI synchronization.

The project intentionally leaves the existing Telegram bot files untouched. Run with any static server, for example `python3 -m http.server 8080` from the repository root.
