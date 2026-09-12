# MyHerzen Apple app icon

The iOS/iPadOS and native macOS targets use
`iOS/MyHerzen/AppIcon.icon`. Its Default, Dark and Mono configuration matches
the approved MyMPSU Icon Composer document, with MyHerzen's own artwork.

- Default uses the original Herzen blue, `#264796` in sRGB, on the Composer
  light surface. The negative pelican and blue central field are retained.
- Dark uses the supplied positive white pelican and white ornament on
  `system-dark`. It is a separate source geometry, not an inversion of Default.
- Mono uses the transparent white dark-geometry layer, allowing iOS to render
  Clear and Tinted without the old flattened white tile or blue residue.
- Both 1024px layers are centered at 0.82 of the original canvas. Composer's
  layer scale stays 1; it must not apply the reduction a second time.

The original user-provided Light and Dark PNGs are preserved in `Source/` and
remain unchanged in the legacy asset catalog. The catalog's previously empty
Tinted slot is filled, and its macOS images now have the declared pixel sizes.
Xcode 26 uses the layered document for the app icon. The document is excluded
from the widget target. On macOS 26+, the app lets the system choose the icon
appearance instead of overriding it with a runtime bitmap; the existing older
macOS behavior is retained.

## Edit and regenerate

Open `iOS/MyHerzen/AppIcon.icon` in Icon Composer to edit composition and
appearance settings. The transparent raster masters and the two original
flattened PNGs are in `Source/`; extraction provenance and limits are described
in [Source/README.md](Source/README.md).

From the repository root on macOS with Xcode and Icon Composer installed:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swiftc -O scripts/export-apple-app-icons.swift -o /tmp/myherzen-export-apple-icons
/tmp/myherzen-export-apple-icons
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift scripts/preview-apple-app-icons.swift
```

The first script refreshes transparent layers and legacy catalog resources
without rewriting the editable Composer JSON. The second uses Apple's `ictool`
to export six native renditions and a local gallery.

[Open the gallery](Previews/index.html) or [the overview PNG](Previews/contact-sheet.png).
These are Icon Composer exports, not screenshots from an iPhone.

## Verification on 12 September 2026

- iOS Simulator and native macOS Debug builds succeeded with Xcode 26.6.
- The compiled catalogs contain AppIcon image stacks for Light, Dark and
  Tintable on iOS, and Aqua, DarkAqua and Tintable on macOS. Both application
  Info.plists select AppIcon. No app-icon size warnings remain.
- The installed iPhone 17 Pro / iOS 26.5 Simulator app's `Assets.car` SHA-256
  matched the newly built app:
  `aa8db46ca2947274f0db41c8aa35c63525c178e9bd8d62da4fa6942c80e63d66`.
- Before modification, the explicitly reinstalled original build already
  selected the supplied white icon in Dark. The observed Clear/Tinted problem
  was the flattened background and poor contrast, not a reproduced Dark-slot
  selection failure.
- The updated icon was displayed on SpringBoard and the user accepted the
  appearance. A full controlled matrix of Default, Dark, Clear Light/Dark,
  Tinted Light/Dark and Auto transitions was not completed. Simulator settings
  were also being changed interactively by the user; incidental screenshots
  are not labelled as proof of a particular mode.
- All six native renditions were separately exported and visually inspected.
  Physical iPhone behavior, older OS appearance switching and macOS Dock
  switching were not tested. Existing non-icon build warnings remain.

Builds used the saved working copy, which contains other uncommitted work.
This icon change preserves that work and does not include Android, Web or API
changes. No distribution signing or release upload was performed.

Home Screen icon style is selected independently from the interface theme;
Auto follows the corresponding system appearance. Clear and Tinted are derived
from Mono, so Dark alone cannot define their appearance.

References: [Apple Icon Composer integration](https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer),
[Apple Home Screen customization](https://support.apple.com/en-gb/guide/iphone/iph385473442/ios).
