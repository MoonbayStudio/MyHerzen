#!/usr/bin/env swift
// Regenerate transparent Icon Composer layers from the preserved user artwork.
// Run from the repository root with Xcode's Swift (DEVELOPER_DIR if needed).
// Updates generated PNGs in Icon Composer and the legacy asset catalog. Leaves
// the editable icon.json, Xcode project, and original iOS light/dark PNGs alone.
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

struct Raster {
    let width: Int
    let height: Int
    var rgba: [UInt8]
    init(width: Int, height: Int) {
        self.width = width; self.height = height
        rgba = .init(repeating: 0, count: width * height * 4)
    }
    init(_ url: URL) throws {
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw ExportError.message("Cannot read \(url.path)")
        }
        width = image.width; height = image.height
        rgba = .init(repeating: 0, count: width * height * 4)
        rgba.withUnsafeMutableBytes { bytes in
            let context = CGContext(data: bytes.baseAddress, width: width, height: height,
                bitsPerComponent: 8, bytesPerRow: width * 4,
                space: CGColorSpace(name: CGColorSpace.sRGB)!,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
            context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
    }
    func image() -> CGImage {
        let data = Data(rgba) as CFData
        return CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
            bytesPerRow: width * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue),
            provider: CGDataProvider(data: data)!, decode: nil, shouldInterpolate: true,
            intent: .defaultIntent)!
    }
    func write(_ url: URL) throws {
        guard let output = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
            throw ExportError.message("Cannot write \(url.path)")
        }
        CGImageDestinationAddImage(output, image(), nil)
        guard CGImageDestinationFinalize(output) else { throw ExportError.message("PNG write failed") }
    }
}
enum ExportError: Error { case message(String) }
func clamp(_ value: Double) -> Double { min(1, max(0, value)) }
func luminance(_ image: Raster, _ index: Int) -> Double {
    let i = index * 4
    return (Double(image.rgba[i]) + Double(image.rgba[i + 1]) + Double(image.rgba[i + 2])) / 3
}
func expand(_ input: [Bool], width: Int, height: Int, radius: Int) -> [Bool] {
    var output = input
    for y in 0..<height { for x in 0..<width where input[y * width + x] {
        for yy in max(0, y - radius)...min(height - 1, y + radius) {
            for xx in max(0, x - radius)...min(width - 1, x + radius) { output[yy * width + xx] = true }
        }
    } }
    return output
}
// White source corners and glass-edge highlights belong to components touching
// the bitmap edge. Remove those components before recovering the white emblem.
func removeBorderComponents(_ input: [Bool], width: Int, height: Int) -> [Bool] {
    var output = input
    var queue: [Int] = []
    for y in 0..<height { for x in 0..<width where x == 0 || y == 0 || x == width - 1 || y == height - 1 {
        let index = y * width + x
        if output[index] { output[index] = false; queue.append(index) }
    } }
    var cursor = 0
    while cursor < queue.count {
        let index = queue[cursor]; cursor += 1
        let x = index % width, y = index / width
        for yy in max(0, y - 1)...min(height - 1, y + 1) {
            for xx in max(0, x - 1)...min(width - 1, x + 1) {
                let next = yy * width + xx
                if output[next] { output[next] = false; queue.append(next) }
            }
        }
    }
    return output
}
struct Extraction {
    let alpha: [Double]
    let background: [Double]
    let reconstruction: Raster
    let errorMean: Double
    let edgeErrorP95: Double
}
func extract(_ input: Raster, dark: Bool) -> Extraction {
    let w = input.width, h = input.height, n = w * h
    var seed = [Bool](repeating: false, count: n)
    for p in 0..<n {
        let i = p * 4
        seed[p] = dark ? luminance(input, p) > 96 : input.rgba[i] < 160
    }
    if dark { seed = removeBorderComponents(seed, width: w, height: h) }
    let support = expand(seed, width: w, height: h, radius: 3)
    // Estimate the smooth backdrop across each source-art segment from nearby
    // uncontaminated pixels on the same scanline. A 3px excluded boundary retains
    // subpixel antialiasing instead of baking the old backdrop into the layer.
    var background = [Double](repeating: 0, count: n * 3)
    for y in 0..<h {
        var anchor = [Bool](repeating: false, count: w)
        for x in 0..<w {
            let p = y * w + x, i = p * 4
            anchor[x] = !support[p] && (dark ? luminance(input, p) < 96 : input.rgba[i] > 160)
        }
        var left = [Int](repeating: -1, count: w), right = left
        var nearest = -1
        for x in 0..<w { if anchor[x] { nearest = x }; left[x] = nearest }
        nearest = -1
        for x in (0..<w).reversed() { if anchor[x] { nearest = x }; right[x] = nearest }
        for x in 0..<w {
            let p = y * w + x
            let l = left[x] < 0 ? right[x] : left[x]
            let r = right[x] < 0 ? left[x] : right[x]
            for c in 0..<3 {
                if l < 0 || r < 0 { background[p * 3 + c] = dark ? 30 : 240; continue }
                // Average a short background-only run to suppress 8-bit dither.
                func sample(_ at: Int) -> Double {
                    var total = 0.0, count = 0.0
                    for xx in max(0, at - 2)...min(w - 1, at + 2) where anchor[xx] {
                        total += Double(input.rgba[(y * w + xx) * 4 + c]); count += 1
                    }
                    return total / max(1, count)
                }
                let a = sample(l), b = sample(r)
                background[p * 3 + c] = l == r ? a : a + (b - a) * Double(x - l) / Double(r - l)
            }
        }
    }
    // The blue source is Display P3, explicitly decoded into sRGB above. Its
    // dominant opaque blue is (38,71,150), not its encoded Display P3 numbers.
    let sourceColor = dark ? [255.0, 255.0, 255.0] : [38.0, 71.0, 150.0]
    var alpha = [Double](repeating: 0, count: n)
    var reconstruction = input
    var allError = 0.0, edgeErrors: [Double] = []
    for p in 0..<n {
        var numerator = 0.0, denominator = 0.0
        for c in 0..<3 {
            let delta = sourceColor[c] - background[p * 3 + c]
            numerator += (Double(input.rgba[p * 4 + c]) - background[p * 3 + c]) * delta
            denominator += delta * delta
        }
        var a = support[p] ? clamp(numerator / max(1, denominator)) : 0
        // Values below one 8-bit coverage step are backdrop/dither uncertainty.
        if a < 1.0 / 255 { a = 0 }
        alpha[p] = a
        if support[p] {
            var error = 0.0
            for c in 0..<3 {
                let value = a * sourceColor[c] + (1 - a) * background[p * 3 + c]
                error += abs(value - Double(input.rgba[p * 4 + c])) / 3
                reconstruction.rgba[p * 4 + c] = UInt8(min(255, max(0, value.rounded())))
            }
            allError += error
            if a > 0.01 && a < 0.99 { edgeErrors.append(error) }
        }
    }
    edgeErrors.sort()
    return Extraction(alpha: alpha, background: background, reconstruction: reconstruction,
        errorMean: allError / Double(support.filter { $0 }.count),
        edgeErrorP95: edgeErrors.isEmpty ? 0 : edgeErrors[min(edgeErrors.count - 1, Int(Double(edgeErrors.count) * 0.95))])
}
func layer(_ alpha: [Double], width: Int, height: Int, color: [UInt8]) -> Raster {
    var result = Raster(width: width, height: height)
    for p in 0..<alpha.count {
        let a = UInt8((clamp(alpha[p]) * 255).rounded())
        for c in 0..<3 { result.rgba[p * 4 + c] = UInt8((Double(color[c]) * Double(a) / 255).rounded()) }
        result.rgba[p * 4 + 3] = a
    }
    return result
}
func scale(_ image: Raster, factor: Double) -> Raster {
    var output = Raster(width: image.width, height: image.height)
    output.rgba.withUnsafeMutableBytes { bytes in
        let context = CGContext(data: bytes.baseAddress, width: image.width, height: image.height,
            bitsPerComponent: 8, bytesPerRow: image.width * 4,
            space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.interpolationQuality = .high
        let w = Double(image.width), h = Double(image.height)
        context.draw(image.image(), in: CGRect(x: w * (1 - factor) / 2, y: h * (1 - factor) / 2,
            width: w * factor, height: h * factor))
    }
    return output
}
func resizeOriginal(_ sourceURL: URL, side: Int, destination: URL) throws {
    // Retain the original profile and opaque pixel format when preparing the
    // legacy macOS sizes. The already-correct 1024px slot remains byte-identical.
    if side == 1024 {
        try Data(contentsOf: sourceURL).write(to: destination, options: .atomic)
        return
    }
    let options: [CFString: Any] = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceThumbnailMaxPixelSize: side,
        kCGImageSourceCreateThumbnailWithTransform: true
    ]
    guard let source = CGImageSourceCreateWithURL(sourceURL as CFURL, nil),
          let image = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary),
          image.width == side, image.height == side,
          let output = CGImageDestinationCreateWithURL(destination as CFURL, UTType.png.identifier as CFString, 1, nil) else {
        throw ExportError.message("Cannot prepare legacy icon size \(side)")
    }
    CGImageDestinationAddImage(output, image, nil)
    guard CGImageDestinationFinalize(output) else { throw ExportError.message("Legacy PNG write failed") }
}
func checkerboard(_ foreground: Raster) -> Raster {
    var result = foreground
    for y in 0..<foreground.height { for x in 0..<foreground.width {
        let p = (y * foreground.width + x) * 4
        let bg = ((x / 32 + y / 32) % 2 == 0) ? 205.0 : 235.0
        let a = Double(foreground.rgba[p + 3]) / 255
        for c in 0..<3 { result.rgba[p + c] = UInt8(min(255, (Double(foreground.rgba[p + c]) + bg * (1 - a)).rounded())) }
        result.rgba[p + 3] = 255
    } }
    return result
}
func sideBySide(_ images: [Raster]) -> Raster {
    let width = images.reduce(0) { $0 + $1.width }, height = images.map(\.height).max()!
    var result = Raster(width: width, height: height)
    var xOffset = 0
    for image in images {
        for y in 0..<image.height {
            let start = (y * width + xOffset) * 4
            result.rgba.replaceSubrange(start..<(start + image.width * 4), with: image.rgba[(y * image.width * 4)..<((y + 1) * image.width * 4)])
        }
        xOffset += image.width
    }
    return result
}
func bounds(_ image: Raster) -> [Int] {
    var minX = image.width, minY = image.height, maxX = -1, maxY = -1
    for y in 0..<image.height { for x in 0..<image.width where image.rgba[(y * image.width + x) * 4 + 3] > 8 {
        minX = min(minX, x); minY = min(minY, y); maxX = max(maxX, x); maxY = max(maxY, y)
    } }
    return [minX, minY, maxX, maxY]
}
let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let design = root.appendingPathComponent("Design/AppIcon")
let source = design.appendingPathComponent("Source")
let layers = design.appendingPathComponent("Layers")
let qa = design.appendingPathComponent("QA")
for directory in [layers, qa] { try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true) }
let originals = [try Raster(source.appendingPathComponent("MyHerzen-Light-original.png")),
                 try Raster(source.appendingPathComponent("MyHerzen-Dark-original.png"))]
guard originals.allSatisfy({ $0.width == 1024 && $0.height == 1024 }) else {
    throw ExportError.message("Expected preserved 1024px originals")
}
var report: [String: Any] = ["scale": 0.82, "colorSpace": "sRGB", "lightColor": "#264796",
    "note": "Light negative pelican and dark positive pelican intentionally retain different source geometry. Error metrics measure recolor-neutral source reconstruction; they are not a claim of lossless vector recovery."]
var previews: [Raster] = []
for (index, name) in ["Light", "Dark"].enumerated() {
    let original = originals[index], extraction = extract(original, dark: index == 1)
    let whiteMaster = layer(extraction.alpha, width: 1024, height: 1024, color: [255, 255, 255])
    try whiteMaster.write(source.appendingPathComponent("MyHerzen-\(name)-alpha-master.png"))
    let color: [UInt8] = index == 0 ? [38, 71, 150] : [255, 255, 255]
    // Scale the coverage once and apply flat colors afterward. This makes each
    // colored version share exactly the same antialiased geometry and margins.
    let coverage = scale(whiteMaster, factor: 0.82)
    let scaledAlpha = stride(from: 3, to: coverage.rgba.count, by: 4).map { Double(coverage.rgba[$0]) / 255 }
    let rendered = layer(scaledAlpha, width: 1024, height: 1024, color: color)
    try rendered.write(layers.appendingPathComponent("MyHerzen-\(name)-foreground.png"))
    try layer(scaledAlpha, width: 1024, height: 1024, color: [0, 0, 0]).write(layers.appendingPathComponent("MyHerzen-\(name)-monochrome.png"))
    try layer(scaledAlpha, width: 1024, height: 1024, color: [255, 255, 255]).write(layers.appendingPathComponent("MyHerzen-\(name)-white.png"))
    try sideBySide([original, extraction.reconstruction, checkerboard(rendered)]).write(qa.appendingPathComponent("\(name)-source-reconstruction-layer.png"))
    previews.append(checkerboard(rendered))
    report[name] = ["boundsAlphaGreaterThan8": bounds(rendered), "reconstructionMeanAbsoluteRGBError0to255": extraction.errorMean,
        "antialiasEdge95PercentileRGBError0to255": extraction.edgeErrorP95,
        "coveragePixelsBeforeScale": extraction.alpha.filter { $0 > 0 }.count,
        "coveragePixelsAfterScale": scaledAlpha.filter { $0 > 0 }.count]
}
try sideBySide(previews).write(qa.appendingPathComponent("transparent-layers-preview.png"))
let json = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
try json.write(to: qa.appendingPathComponent("extraction-report.json"))
// Icon Composer's JSON remains a hand-editable source. Refresh only its two
// referenced artwork files so the build cannot silently use stale PNG layers.
let composerAssets = root.appendingPathComponent("iOS/MyHerzen/AppIcon.icon/Assets")
try FileManager.default.createDirectory(at: composerAssets, withIntermediateDirectories: true)
for name in ["MyHerzen-Light-foreground.png", "MyHerzen-Dark-foreground.png"] {
    try Data(contentsOf: layers.appendingPathComponent(name)).write(to: composerAssets.appendingPathComponent(name), options: .atomic)
}
// Keep the supplied iOS Light/Dark fallback icons byte-for-byte unchanged. Fill
// the formerly empty tinted slot, and derive legacy Mac sizes from the preserved
// original Light artwork rather than repeatedly resizing already-small outputs.
let appIconSet = root.appendingPathComponent("iOS/MyHerzen/Assets.xcassets/AppIcon.appiconset")
let contentsURL = appIconSet.appendingPathComponent("Contents.json")
var manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: contentsURL)) as! [String: Any]
var entries = manifest["images"] as! [[String: Any]]
let tintedName = "Icon-iOS-Tinted-1024x1024@1x.png"
guard let tintedIndex = entries.firstIndex(where: { entry in
    (entry["appearances"] as? [[String: String]])?.contains(where: { $0["appearance"] == "luminosity" && $0["value"] == "tinted" }) == true
}) else { throw ExportError.message("Expected an existing tinted app-icon slot") }
entries[tintedIndex]["filename"] = tintedName
try Data(contentsOf: layers.appendingPathComponent("MyHerzen-Dark-white.png")).write(to: appIconSet.appendingPathComponent(tintedName), options: .atomic)
for entry in entries where entry["idiom"] as? String == "mac" {
    guard let filename = entry["filename"] as? String,
          let sizeText = entry["size"] as? String,
          let points = Int(sizeText.split(separator: "x")[0]),
          let scaleText = entry["scale"] as? String,
          let scale = Int(scaleText.dropLast()) else { throw ExportError.message("Invalid declared macOS icon size") }
    try resizeOriginal(source.appendingPathComponent("MyHerzen-Light-original.png"), side: points * scale,
                       destination: appIconSet.appendingPathComponent(filename))
}
manifest["images"] = entries
var manifestData = try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
manifestData.append(0x0A)
try manifestData.write(to: contentsURL, options: .atomic)
print(String(data: json, encoding: .utf8)!)
print("Exported transparent masters, 0.82 layers, QA comparisons, Composer PNGs, and legacy fallback PNGs.")
