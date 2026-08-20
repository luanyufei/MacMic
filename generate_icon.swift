import AppKit

let size: CGFloat = 512
let img = NSImage(size: NSSize(width: size, height: size))
img.lockFocus()

// Background rounded rect
let bgGradient = NSGradient(starting: NSColor(calibratedRed: 0.08, green: 0.45, blue: 0.95, alpha: 1.0),
                            ending: NSColor(calibratedRed: 0.02, green: 0.20, blue: 0.65, alpha: 1.0))!
let bgPath = NSBezierPath(roundedRect: NSRect(x: 32, y: 32, width: 448, height: 448), xRadius: 100, yRadius: 100)
bgGradient.draw(in: bgPath, angle: -45)

// Outer Sound Waves
let waveColor = NSColor(calibratedRed: 0.4, green: 0.8, blue: 1.0, alpha: 0.7)
waveColor.setStroke()

let waveLeft = NSBezierPath()
waveLeft.lineWidth = 14
waveLeft.lineCapStyle = .round
waveLeft.appendArc(withCenter: NSPoint(x: 256, y: 270), radius: 150, startAngle: 140, endAngle: 220, clockwise: false)
waveLeft.stroke()

let waveRight = NSBezierPath()
waveRight.lineWidth = 14
waveRight.lineCapStyle = .round
waveRight.appendArc(withCenter: NSPoint(x: 256, y: 270), radius: 150, startAngle: -40, endAngle: 40, clockwise: false)
waveRight.stroke()

// Mic Capsule
let micGradient = NSGradient(starting: NSColor.white, ending: NSColor(calibratedRed: 0.85, green: 0.92, blue: 1.0, alpha: 1.0))!
let micBody = NSBezierPath(roundedRect: NSRect(x: 206, y: 200, width: 100, height: 180), xRadius: 50, yRadius: 50)
micGradient.draw(in: micBody, angle: -90)

// Mic Arc Stand
NSColor.white.setStroke()
let standArc = NSBezierPath()
standArc.lineWidth = 18
standArc.lineCapStyle = .round
standArc.appendArc(withCenter: NSPoint(x: 256, y: 270), radius: 85, startAngle: 180, endAngle: 0, clockwise: true)
standArc.stroke()

// Pole & Base
let standPole = NSBezierPath()
standPole.lineWidth = 18
standPole.lineCapStyle = .round
standPole.move(to: NSPoint(x: 256, y: 185))
standPole.line(to: NSPoint(x: 256, y: 110))
standPole.move(to: NSPoint(x: 180, y: 110))
standPole.line(to: NSPoint(x: 332, y: 110))
standPole.stroke()

img.unlockFocus()

let fm = FileManager.default
try? fm.createDirectory(atPath: "WOMic.iconset", withIntermediateDirectories: true)

let sizes = [16, 32, 64, 128, 256, 512]
for s in sizes {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: s, pixelsHigh: s, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .calibratedRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    rep.size = NSSize(width: s, height: s)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    img.draw(in: NSRect(x: 0, y: 0, width: s, height: s), from: NSRect(x: 0, y: 0, width: size, height: size), operation: .copy, fraction: 1.0)
    NSGraphicsContext.restoreGraphicsState()
    if let data = rep.representation(using: .png, properties: [:]) {
        try? data.write(to: URL(fileURLWithPath: "WOMic.iconset/icon_\(s)x\(s).png"))
    }
    
    if s <= 256 {
        let s2 = s * 2
        let rep2 = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: s2, pixelsHigh: s2, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .calibratedRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        rep2.size = NSSize(width: s2, height: s2)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep2)
        img.draw(in: NSRect(x: 0, y: 0, width: s2, height: s2), from: NSRect(x: 0, y: 0, width: size, height: size), operation: .copy, fraction: 1.0)
        NSGraphicsContext.restoreGraphicsState()
        if let data2 = rep2.representation(using: .png, properties: [:]) {
            try? data2.write(to: URL(fileURLWithPath: "WOMic.iconset/icon_\(s)x\(s)@2x.png"))
        }
    }
}
print("Generated all icon sizes.")
