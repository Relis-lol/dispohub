# Screenshots

This folder is where the screenshots referenced in the main
[README](../../README.md) belong:

- `dashboard.png` — management dashboard overview
- `vehicle-detail.png` — a vehicle record page
- `driver-chat.png` — the driver mobile chat view
- `calendar.png` — the month calendar grid

**These are not yet included in this release.** They need to be captured
against a running instance seeded with demo data (`SEED_ON_STARTUP=true`,
the default) — all data shown must be the built-in fictional demo data, not
any real company's information. A short guide:

1. Start the app (`docker compose up --build` or the local dev setup).
2. Log in with one of the [demo accounts](../../README.md#first-login).
3. Capture: the management dashboard, a vehicle detail page, the driver
   chat view (narrow/mobile viewport), and the calendar grid.
4. Crop out the browser chrome, save as PNG in this folder using the
   filenames above, and update the `<img>`/markdown references in
   `README.md` if you use different names.

Until these are added, the screenshots section of the README will show
broken image links on GitHub — please add them before or shortly after
the first release, or remove that section from the README if you'd rather
ship without it for now.
