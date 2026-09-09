import AppKit

// Аргументы: out.png  h gap x0 maxW  w1 w2 w3 w4 w5
let a = CommandLine.arguments
let out = a[1]
let h = Double(a[2])!, gap = Double(a[3])!, x0 = Double(a[4])!, maxW = Double(a[5])!
let fracs = (6...10).map { Double(a[$0])! }

let N = 1024.0
let top = NSColor(deviceRed: 138/255.0, green: 33/255.0, blue: 38/255.0, alpha: 1)
let bot = NSColor(deviceRed: 178/255.0, green: 57/255.0, blue: 58/255.0, alpha: 1)
let bar = NSColor(deviceRed: 249/255.0, green: 246/255.0, blue: 246/255.0, alpha: 1)

let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(N), pixelsHigh: Int(N),
  bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
  colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSGradient(starting: bot, ending: top)!.draw(in: NSRect(x: 0, y: 0, width: N, height: N), angle: 90)

let block = 5 * h + 4 * gap
let yTop = (N - block) / 2                      // отступ сверху, координаты сверху вниз
precondition(yTop > 100, "блок полосок слишком высокий: \(block)")
precondition(x0 + maxW <= N - x0 + 0.5, "полоски выходят за правое поле")
bar.set()
for (i, f) in fracs.enumerated() {
  let w = maxW * f
  let yFromTop = yTop + Double(i) * (h + gap)
  let y = N - yFromTop - h                      // Cocoa: ось Y снизу вверх
  NSBezierPath(roundedRect: NSRect(x: x0, y: y, width: w, height: h),
               xRadius: h / 2, yRadius: h / 2).fill()
}
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
print("\(out)  блок \(Int(block))  поля свеху/снизу \(Int(yTop))  лево \(Int(x0)) право \(Int(N - x0 - maxW))")
