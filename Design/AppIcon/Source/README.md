# Preserved MyHerzen artwork and transparent masters

The two `MyHerzen-*-original.png` files are byte-for-byte copies of the user-designated
light and dark app icons. The light artwork intentionally contains a blue field
with a negative pelican; the dark artwork intentionally contains a positive white
pelican on a dark field. These are different authoritative appearance variants.
Do not replace one with a recoloring of the other.

Original SHA-256 values:

- Light: `ebb1ebbaa7e29f6651699f0a9a4c8c8205a22a7fd6d804ef8bc06351dd1ba6b7`
- Dark: `eefb4e786f309bf0a51b3a9f60bcb4f068f9552049968e3a504d65740408711a`

The separate `herzenicon.imageset/herzenicon.png` asset was also inspected. Its
larger composition and contaminated semitransparent pixels do not match the
designated app-icon artwork, so it is not used to generate these layers.

The `MyHerzen-*-alpha-master.png` files are unscaled, transparent, white coverage
masters extracted from the original raster images. They are editable raster
sources, not traced vectors. The source art and its transparency are preserved
without generative reconstruction or redrawing.

## Regeneration

From the repository root:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swiftc -O scripts/export-apple-app-icons.swift -o /tmp/myherzen-export-apple-icons
/tmp/myherzen-export-apple-icons
```

The script uses Swift, CoreGraphics, and ImageIO. It reads the preserved originals
and writes coverage masters, transparent layers, and the QA comparisons. It also
copies the two foreground PNGs into `iOS/MyHerzen/AppIcon.icon/Assets`, fills the
legacy asset catalog's tinted slot with the white dark-geometry layer, and prepares
the ten declared macOS image sizes from the preserved light original. The latter
all contained identical 1024px source files before size correction. Resizing uses
ImageIO and retains the original color profile. The 1024px slot remains identical.

The script does not modify the preserved originals, the original iOS Light/Dark
fallback PNGs, the Xcode project, or the editable `AppIcon.icon/icon.json` document.

The light original is Display P3. After color-managed decoding into sRGB, its
dominant opaque blue is `(38,71,150)`, or `#264796`. This original MyHerzen blue
is retained in the light layer. Dark is white. Both geometries also have white
and neutral black layer exports for composition and monochrome appearances.

## Extraction and quality limits

The script locates colored or white foreground pixels and expands their support
by three pixels to retain edge coverage. In the dark source it first removes
light components connected to the bitmap border, which removes white external
corners and the old icon's edge highlights. It estimates the smooth backdrop
under each artwork segment using uncontaminated pixels on the same scanline.

For foreground color `F`, observed source pixel `I`, and local backdrop `B`, alpha
is the clamped least-squares solution of `I = alpha * F + (1 - alpha) * B`.
The resulting coverage is scaled once by `0.82` around the exact canvas center.
Each appearance's exported color is applied after scaling, so its color variants
share identical alpha and margins. All output layers are 1024 × 1024. Do not
apply another 0.82 scale in Icon Composer.

The backdrop is estimated from flattened raster art, so this is not a claim of
lossless vector recovery. `../QA/extraction-report.json` records reconstruction
error before recoloring and rescaling. The three-panel QA images show the source,
its reconstruction, and the transparent layer over a checkerboard. Reconstruction
errors are measured inside the extracted support; the original bitmap outside
that support is retained only in the comparison image.

Verified run: mean RGB reconstruction error was 0.77/255 for Light and 0.53/255
for Dark. The 95th-percentile antialiased-edge error was 2.31/255 and 0.99/255,
respectively. These are numerical extraction checks, not system appearance tests.
