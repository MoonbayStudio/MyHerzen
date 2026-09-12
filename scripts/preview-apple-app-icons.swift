#!/usr/bin/env swift
// Run from the repository root, or pass --root /absolute/path/to/MyHerzen.
// Only writes preview artifacts. It never edits the Icon Composer document or app assets.
import AppKit
import CryptoKit
import Foundation

struct PreviewError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

struct Rendition {
    let name: String
    let title: String
    let subtitle: String
    var filename: String { "Apple-\(name).png" }
}

let renditions = [
    Rendition(name: "Default", title: "Светлая", subtitle: "Default"),
    Rendition(name: "Dark", title: "Тёмная", subtitle: "Dark"),
    Rendition(name: "ClearLight", title: "Прозрачная · светлая", subtitle: "ClearLight"),
    Rendition(name: "ClearDark", title: "Прозрачная · тёмная", subtitle: "ClearDark"),
    Rendition(name: "TintedLight", title: "Тонированная · светлая", subtitle: "TintedLight"),
    Rendition(name: "TintedDark", title: "Тонированная · тёмная", subtitle: "TintedDark")
]

func option(_ name: String) throws -> String? {
    guard let index = CommandLine.arguments.firstIndex(of: name) else { return nil }
    guard CommandLine.arguments.indices.contains(index + 1) else {
        throw PreviewError(message: "Missing value for \(name)")
    }
    return CommandLine.arguments[index + 1]
}

@discardableResult
func run(_ executable: URL, _ arguments: [String]) throws -> String {
    let process = Process()
    process.executableURL = executable
    process.arguments = arguments
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    try process.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    let output = String(decoding: data, as: UTF8.self)
    guard process.terminationStatus == 0 else {
        throw PreviewError(message: "\(executable.lastPathComponent) failed (\(process.terminationStatus)):\n\(output)")
    }
    return output
}

func sha256(_ url: URL) throws -> String {
    SHA256.hash(data: try Data(contentsOf: url)).map { String(format: "%02x", $0) }.joined()
}

func sourceHashes(document: URL, root: URL) throws -> [[String: String]] {
    let enumerator = FileManager.default.enumerator(at: document, includingPropertiesForKeys: [.isRegularFileKey])
    var sources: [[String: String]] = []
    while let file = enumerator?.nextObject() as? URL {
        if try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true {
            sources.append(["file": String(file.path.dropFirst(root.path.count + 1)), "sha256": try sha256(file)])
        }
    }
    return sources.sorted { $0["file", default: ""] < $1["file", default: ""] }
}

func color(_ hex: UInt32) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 255) / 255,
            green: CGFloat((hex >> 8) & 255) / 255,
            blue: CGFloat(hex & 255) / 255, alpha: 1)
}

func contactSheet(output: URL) throws {
    let width = 1520, height = 2100
    guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
        let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
        throw PreviewError(message: "Cannot create preview canvas")
    }
    NSGraphicsContext.saveGraphicsState()
    defer { NSGraphicsContext.restoreGraphicsState() }
    NSGraphicsContext.current = context
    context.imageInterpolation = .high

    func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> NSRect {
        NSRect(x: x, y: CGFloat(height) - y - h, width: w, height: h)
    }
    func text(_ value: String, x: CGFloat, y: CGFloat, w: CGFloat, h: CGFloat,
              size: CGFloat, weight: NSFont.Weight = .regular, ink: UInt32 = 0x1E293B,
              alignment: NSTextAlignment = .left) {
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = alignment
        paragraph.lineBreakMode = .byWordWrapping
        (value as NSString).draw(in: rect(x, y, w, h), withAttributes: [
            .font: NSFont.systemFont(ofSize: size, weight: weight),
            .foregroundColor: color(ink), .paragraphStyle: paragraph
        ])
    }
    color(0xF3F4F6).setFill()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    text("МОЙ ГЕРЦЕНА  /  APP ICON", x: 60, y: 42, w: 1400, h: 28, size: 20, weight: .semibold, ink: 0x526176)
    text("Шесть вариантов иконки", x: 60, y: 86, w: 1400, h: 62, size: 48, weight: .bold)
    text("Экспорт Icon Composer · iOS · 1024 × 1024 px", x: 62, y: 153, w: 1396, h: 36, size: 25, ink: 0x526176)

    for (index, rendition) in renditions.enumerated() {
        let x = CGFloat(60 + (index % 2) * 716)
        let y = CGFloat(224 + (index / 2) * 580)
        color(0xE6E8EC).setFill()
        NSBezierPath(roundedRect: rect(x, y, 684, 552), xRadius: 26, yRadius: 26).fill()
        text(rendition.title, x: x + 30, y: y + 23, w: 624, h: 38, size: 28, weight: .semibold)
        text(rendition.subtitle, x: x + 30, y: y + 64, w: 624, h: 28, size: 19, ink: 0x526176)
        guard let image = NSImage(contentsOf: output.appendingPathComponent(rendition.filename)) else {
            throw PreviewError(message: "Cannot open \(rendition.filename)")
        }
        image.draw(in: rect(x + 150, y + 104, 384, 384), from: .zero, operation: .sourceOver, fraction: 1)
        image.draw(in: rect(x + 30, y + 464, 60, 60), from: .zero, operation: .sourceOver, fraction: 1)
        text("Образец 60 px", x: x + 108, y: y + 483, w: 250, h: 27, size: 18, ink: 0x526176)
    }
    text("Превью из сохранённого AppIcon.icon. Это экспорт Icon Composer, а не снимки экрана iOS.",
         x: 62, y: 1990, w: 1396, h: 35, size: 22, ink: 0x526176)
    text("Clear и Tinted показаны с параметрами экспорта Apple; вид на устройстве зависит от обоев и настроек.",
         x: 62, y: 2030, w: 1396, h: 36, size: 20, ink: 0x526176)
    context.flushGraphics()
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        throw PreviewError(message: "Cannot encode contact sheet")
    }
    try png.write(to: output.appendingPathComponent("contact-sheet.png"), options: .atomic)
}

func gallery(generation: String) -> String {
    let cards = renditions.map { rendition in
        """
        <article class="card" aria-labelledby="title-\(rendition.name)">
          <header><h2 id="title-\(rendition.name)">\(rendition.title)</h2><p>\(rendition.subtitle)</p></header>
          <a class="art" href="\(rendition.filename)" aria-label="Открыть \(rendition.title.lowercased()) в исходном размере"><img src="\(rendition.filename)" width="1024" height="1024" alt="Мой Герцена — \(rendition.title.lowercased())"></a>
          <footer><div class="sample"><img src="\(rendition.filename)" width="60" height="60" alt=""><span>Образец 60 px</span></div><a href="\(rendition.filename)" download>PNG · 1024 px</a></footer>
        </article>
        """
    }.joined(separator: "\n")
    return """
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <meta name="color-scheme" content="light">
      <title>Мой Герцена — варианты иконки</title>
      <style>
        * { box-sizing: border-box; }
        body { margin: 0; color: #1e293b; background: #f3f4f6; font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        main { max-width: 1160px; margin: auto; padding: 44px 24px 56px; }
        .kicker { margin: 0 0 12px; font-size: 13px; font-weight: 700; letter-spacing: .1em; color: #526176; }
        h1 { margin: 0 0 12px; font-size: clamp(30px, 4vw, 46px); line-height: 1.15; letter-spacing: -.035em; }
        .intro { max-width: 850px; margin: 0 0 24px; font-size: 18px; color: #526176; }
        a { color: #264796; text-underline-offset: 3px; }
        a:focus-visible { outline: 3px solid #264796; outline-offset: 5px; border-radius: 4px; }
        .links { display: flex; flex-wrap: wrap; gap: 12px 24px; margin: 0 0 30px; }
        .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
        .card { padding: 24px; background: #e6e8ec; border: 1px solid #dce0e5; border-radius: 22px; min-width: 0; }
        h2 { margin: 0; font-size: clamp(19px, 2.1vw, 25px); line-height: 1.3; }
        .card header p { color: #526176; margin: 5px 0 14px; font-size: 14px; }
        .art { display: block; max-width: 350px; margin: 0 auto 20px; }
        .art img { display: block; width: 100%; height: auto; }
        .card footer { display: flex; align-items: center; flex-wrap: wrap; justify-content: space-between; gap: 14px; font-size: 13px; }
        .sample { display: flex; align-items: center; gap: 12px; color: #526176; }
        .sample img { display: block; flex: none; }
        .legend { margin-top: 30px; padding: 24px 28px; border: 1px solid #dce0e5; border-radius: 18px; background: white; }
        .legend h2 { font-size: 20px; margin-bottom: 10px; }
        .legend p { margin: 8px 0; color: #526176; }
        code { overflow-wrap: anywhere; font-size: .9em; }
        @media (max-width: 640px) { main { padding: 28px 16px; } .grid { grid-template-columns: 1fr; gap: 18px; } .card { padding: 20px; } .legend { padding: 20px; } }
      </style>
    </head>
    <body>
      <main>
        <p class="kicker">МОЙ ГЕРЦЕНА / APP ICON</p>
        <h1>Шесть вариантов иконки</h1>
        <p class="intro">Экспорт сохранённого документа Icon Composer. Светлые и тёмные варианты показаны попарно: стандартные, прозрачные и тонированные.</p>
        <nav class="links" aria-label="Файлы превью"><a href="contact-sheet.png">Общий лист PNG</a><a href="export-metadata.json">Параметры и контрольные суммы</a><a href="../../../scripts/preview-apple-app-icons.swift">Скрипт повторного экспорта</a></nav>
        <section class="grid" aria-label="Варианты иконки">
        \(cards)
        </section>
        <aside class="legend" aria-labelledby="legend-title">
          <h2 id="legend-title">Как читать это превью</h2>
          <p>Все шесть PNG созданы утилитой <code>ictool</code> из <code>iOS/MyHerzen/AppIcon.icon</code>: платформа iOS, Design Generation \(generation), размер 1024 × 1024 px, scale 1. Тонирование использует параметры Apple по умолчанию.</p>
          <p><strong>Это экспорт Icon Composer, а не снимки экрана iOS.</strong> Устройство может менять эффекты Clear и Tinted в зависимости от обоев, цвета тонирования и системных настроек. Эта галерея не подтверждает системное переключение вариантов.</p>
          <p>Большой образец позволяет рассмотреть эмблему; малый показан в размере 60 CSS px. Полноразмерные PNG открываются нажатием на иконку. Фон карточек нейтральный и одинаковый у всех вариантов.</p>
        </aside>
      </main>
    </body>
    </html>
    """
}

do {
    if CommandLine.arguments.contains("--help") {
        print("Usage: preview-apple-app-icons [--root <repository>] [--output <directory>] [--ictool <executable>] [--design-generation 26|27]")
        exit(0)
    }
    let root = URL(fileURLWithPath: try option("--root") ?? FileManager.default.currentDirectoryPath).standardizedFileURL
    let document = root.appendingPathComponent("iOS/MyHerzen/AppIcon.icon")
    let output = URL(fileURLWithPath: try option("--output") ?? root.appendingPathComponent("Design/AppIcon/Previews").path).standardizedFileURL
    let ictool = URL(fileURLWithPath: try option("--ictool") ?? "/Applications/Icon Composer.app/Contents/Executables/ictool")
    let generation = try option("--design-generation") ?? "26"
    guard ["26", "27"].contains(generation) else { throw PreviewError(message: "Design generation must be 26 or 27") }
    guard FileManager.default.fileExists(atPath: document.appendingPathComponent("icon.json").path) else {
        throw PreviewError(message: "Missing \(document.path). Run from the repository root or pass --root.")
    }
    let version = try run(ictool, ["--version"])
    let sources = try sourceHashes(document: document, root: root)
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    var outputs: [[String: Any]] = []
    for rendition in renditions {
        let file = output.appendingPathComponent(rendition.filename)
        let arguments = [document.path, "--export-image", "--output-file", file.path, "--platform", "iOS",
                         "--rendition", rendition.name, "--width", "1024", "--height", "1024", "--scale", "1",
                         "--design-generation", generation]
        try run(ictool, arguments)
        guard let image = NSBitmapImageRep(data: try Data(contentsOf: file)), image.pixelsWide == 1024, image.pixelsHigh == 1024 else {
            throw PreviewError(message: "Unexpected exported dimensions: \(file.path)")
        }
        outputs.append(["rendition": rendition.name, "file": rendition.filename, "sha256": try sha256(file)])
        print("Exported \(rendition.name): \(file.path)")
    }
    guard sources == (try sourceHashes(document: document, root: root)) else {
        throw PreviewError(message: "The Icon Composer document changed during export. Run again after saving the document.")
    }
    try contactSheet(output: output)
    try gallery(generation: generation).write(to: output.appendingPathComponent("index.html"), atomically: true, encoding: .utf8)
    let metadata: [String: Any] = [
        "description": "Native Icon Composer exports, not iOS screenshots",
        "ictoolVersion": (try? JSONSerialization.jsonObject(with: Data(version.utf8))) ?? version,
        "platform": "iOS", "designGeneration": Int(generation)!, "width": 1024, "height": 1024,
        "scale": 1, "tint": "Icon Composer defaults; no tint-color or tint-strength override",
        "sources": sources, "exports": outputs,
        "contactSheet": ["file": "contact-sheet.png", "width": 1520, "height": 2100],
        "regenerate": "DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift scripts/preview-apple-app-icons.swift --design-generation \(generation)"
    ]
    let data = try JSONSerialization.data(withJSONObject: metadata, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
    try data.write(to: output.appendingPathComponent("export-metadata.json"), options: .atomic)
    print("Gallery: \(output.appendingPathComponent("index.html").path)")
} catch {
    FileHandle.standardError.write(Data("error: \(error.localizedDescription)\n".utf8))
    exit(1)
}
