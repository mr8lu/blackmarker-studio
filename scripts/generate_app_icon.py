"""Generate the Apple HIG-compliant macOS app icon (SVG + PNG + ICNS) for AI Blackmarker.

Follows https://developer.apple.com/design/human-interface-guidelines/app-icons:
- 1024x1024 canvas with 824x824 continuous superellipse body (100px outer margin).
- 544x688 vertical document keyline alignment.
- 90-degree top-down ambient + drop shadow lighting model.
- Single iconic metaphor: a bold black redaction bar and a 45-degree floating chisel marker.
"""

import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT_DIR / "assets" / "icon"
STATIC_DIR = ROOT_DIR / "src" / "redact_gov" / "api" / "static"


HIG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <!-- 90-degree Top-Down macOS Squircle Surface -->
    <linearGradient id="squircleSurface" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="100%" stop-color="#CBD5E1"/>
    </linearGradient>

    <!-- Subtle Top-Down Inner Bevel -->
    <linearGradient id="squircleStroke" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.90"/>
      <stop offset="100%" stop-color="#94A3B8" stop-opacity="0.45"/>
    </linearGradient>

    <!-- Obsidian Blackmarker Ink -->
    <linearGradient id="inkBar" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#090D16"/>
    </linearGradient>

    <!-- 45-degree Floating Marker Barrel -->
    <linearGradient id="markerBody" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="35%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#090D16"/>
    </linearGradient>

    <!-- Subtle Brand Accent Band (Electric Indigo-Blue) -->
    <linearGradient id="brandBand" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#2563EB"/>
    </linearGradient>

    <!-- Apple HIG 90-degree Top-Down Shadow -->
    <filter id="higShadow" x="-15%" y="-15%" width="130%" height="135%">
      <feDropShadow dx="0" dy="26" stdDeviation="24" flood-color="#000000" flood-opacity="0.32"/>
    </filter>

    <filter id="toolShadow" x="-20%" y="-20%" width="140%" height="145%">
      <feDropShadow dx="0" dy="22" stdDeviation="18" flood-color="#090D16" flood-opacity="0.42"/>
    </filter>
  </defs>

  <!-- 1. macOS 824x824 Continuous Squircle (Document Surface) -->
  <rect x="100" y="100" width="824" height="824" rx="185" ry="185"
        fill="url(#squircleSurface)"
        stroke="url(#squircleStroke)"
        stroke-width="6"
        filter="url(#higShadow)"/>

  <!-- 2. Minimalist Document Context Lines (Centered on 688px Keyline) -->
  <rect x="224" y="276" width="320" height="36" rx="18" fill="#94A3B8" opacity="0.48"/>
  <rect x="224" y="348" width="480" height="36" rx="18" fill="#94A3B8" opacity="0.48"/>

  <!-- 3. The Iconic Blackmarker Strike (Single Bold Redaction Bar) -->
  <rect x="212" y="454" width="576" height="116" rx="28" fill="url(#inkBar)"/>

  <!-- Lower Context Line -->
  <rect x="224" y="640" width="410" height="36" rx="18" fill="#94A3B8" opacity="0.48"/>
  <rect x="224" y="712" width="260" height="36" rx="18" fill="#94A3B8" opacity="0.48"/>

  <!-- 4. Apple HIG 45-Degree Floating Tool (Chisel-Tip Marker) -->
  <g transform="translate(650, 480) rotate(-45)" filter="url(#toolShadow)">
    <!-- Chisel Felt Tip touching the Redaction Bar -->
    <path d="M -130 10 L -64 -26 L -64 34 L -130 34 Z" fill="#090D16"/>
    <!-- Tapered Nozzle -->
    <path d="M -64 -28 L -16 -44 L -16 44 L -64 34 Z" fill="#1E293B"/>
    <!-- Minimalist Accent Ring -->
    <rect x="-18" y="-46" width="22" height="92" rx="5" fill="url(#brandBand)"/>
    <!-- Cylindrical Marker Body (Extends slightly toward top-right keyline) -->
    <rect x="4" y="-52" width="340" height="104" rx="34" fill="url(#markerBody)"/>
    <!-- Top-Down Specular Highlight along Marker Barrel -->
    <rect x="26" y="-34" width="290" height="14" rx="7" fill="#FFFFFF" opacity="0.18"/>
  </g>
</svg>
"""


def render_hig_macos_png(output_png: Path) -> None:
    """Render the Apple HIG 1024x1024 icon via CoreGraphics with exact 90-degree lighting."""
    swift_code = """
import AppKit
import CoreGraphics
import Foundation

let outPath = CommandLine.arguments[1]
let size = 1024
let cs = CGColorSpaceCreateDeviceRGB()

guard let ctx = CGContext(
    data: nil,
    width: size,
    height: size,
    bitsPerComponent: 8,
    bytesPerRow: size * 4,
    space: cs,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
) else { exit(1) }

// Flip coordinate system so (0,0) is top-left (matching SVG)
ctx.translateBy(x: 0, y: CGFloat(size))
ctx.scaleBy(x: 1.0, y: -1.0)
ctx.clear(CGRect(x: 0, y: 0, width: size, height: size))

func rgba(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1.0) -> CGColor {
    CGColor(srgbRed: r / 255.0, green: g / 255.0, blue: b / 255.0, alpha: a)
}

func fillRounded(_ rect: CGRect, radius: CGFloat, color: CGColor) {
    let p = CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil)
    ctx.addPath(p)
    ctx.setFillColor(color)
    ctx.fillPath()
}

// 1. Apple HIG 824x824 Squircle (100px padding on 1024x1024 canvas)
let squircleRect = CGRect(x: 100, y: 100, width: 824, height: 824)
let squirclePath = CGPath(roundedRect: squircleRect, cornerWidth: 185, cornerHeight: 185, transform: nil)

ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: -24), blur: 36, color: rgba(0, 0, 0, 0.30))
ctx.addPath(squirclePath)
ctx.setFillColor(rgba(241, 245, 249))
ctx.fillPath()
ctx.restoreGState()

// Warm tactile paper-white to cool-silver gradient on the squircle body
ctx.saveGState()
ctx.addPath(squirclePath)
ctx.clip()
if let surfaceGrad = CGGradient(
    colorsSpace: cs,
    colors: [rgba(252, 253, 255), rgba(214, 222, 233)] as CFArray,
    locations: [0.0, 1.0]
) {
    ctx.drawLinearGradient(
        surfaceGrad,
        start: CGPoint(x: 512, y: 100),
        end: CGPoint(x: 512, y: 924),
        options: []
    )
}
ctx.restoreGState()

// Crisp inner specular rim
ctx.saveGState()
ctx.addPath(squirclePath)
ctx.setStrokeColor(rgba(255, 255, 255, 0.85))
ctx.setLineWidth(5.0)
ctx.strokePath()
ctx.restoreGState()

// 2. Minimalist Document Lines (aligned to 688px inner keyline)
fillRounded(CGRect(x: 224, y: 276, width: 320, height: 36), radius: 18, color: rgba(148, 163, 184, 0.45))
fillRounded(CGRect(x: 224, y: 348, width: 480, height: 36), radius: 18, color: rgba(148, 163, 184, 0.45))

// 3. The Iconic Blackmarker Strike (Single Bold Obsidian Bar)
let strikeRect = CGRect(x: 212, y: 454, width: 576, height: 116)
let strikePath = CGPath(roundedRect: strikeRect, cornerWidth: 28, cornerHeight: 28, transform: nil)
ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: -6), blur: 12, color: rgba(9, 13, 22, 0.18))
ctx.addPath(strikePath)
ctx.setFillColor(rgba(12, 16, 23))
ctx.fillPath()
ctx.restoreGState()

// Lower Document Lines
fillRounded(CGRect(x: 224, y: 640, width: 410, height: 36), radius: 18, color: rgba(148, 163, 184, 0.45))
fillRounded(CGRect(x: 224, y: 712, width: 260, height: 36), radius: 18, color: rgba(148, 163, 184, 0.45))

// 4. Apple HIG 45-Degree Floating Chisel Marker Tool
ctx.saveGState()
ctx.translateBy(x: 650, y: 480)
ctx.rotate(by: -45.0 * .pi / 180.0)
ctx.setShadow(offset: CGSize(width: -12, height: -20), blur: 26, color: rgba(9, 13, 22, 0.42))

// Chisel Felt Nib
let nib = CGMutablePath()
nib.move(to: CGPoint(x: -130, y: 10))
nib.addLine(to: CGPoint(x: -64, y: -26))
nib.addLine(to: CGPoint(x: -64, y: 34))
nib.addLine(to: CGPoint(x: -130, y: 34))
nib.closeSubpath()
ctx.addPath(nib)
ctx.setFillColor(rgba(9, 13, 22))
ctx.fillPath()

// Tapered Collar
let collar = CGMutablePath()
collar.move(to: CGPoint(x: -64, y: -28))
collar.addLine(to: CGPoint(x: -16, y: -44))
collar.addLine(to: CGPoint(x: -16, y: 44))
collar.addLine(to: CGPoint(x: -64, y: 34))
collar.closeSubpath()
ctx.addPath(collar)
ctx.setFillColor(rgba(30, 41, 59))
ctx.fillPath()

// Minimalist Brand Accent Ring
fillRounded(CGRect(x: -18, y: -46, width: 22, height: 92), radius: 5, color: rgba(14, 165, 233))

// Matte Obsidian Marker Barrel
let barrelRect = CGRect(x: 4, y: -52, width: 340, height: 104)
let barrelPath = CGPath(roundedRect: barrelRect, cornerWidth: 34, cornerHeight: 34, transform: nil)
ctx.addPath(barrelPath)
ctx.setFillColor(rgba(17, 23, 34))
ctx.fillPath()

// Top-down specular highlight on barrel
fillRounded(CGRect(x: 28, y: -34, width: 286, height: 12), radius: 6, color: rgba(255, 255, 255, 0.18))
ctx.restoreGState()

guard let cgImage = ctx.makeImage() else { exit(1) }
let rep = NSBitmapImageRep(cgImage: cgImage)
guard let data = rep.representation(using: .png, properties: [:]) else { exit(1) }
try data.write(to: URL(fileURLWithPath: outPath))
"""
    subprocess.run(["swift", "-e", swift_code, str(output_png)], check=True)
    print(f"[Icon] Rendered Apple HIG macOS PNG -> {output_png}")


def build_icns_from_png(source_png: Path, output_icns: Path) -> None:
    iconset_dir = source_png.parent / "AppIcon.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for px, filename in sizes:
        dest = iconset_dir / filename
        subprocess.run(
            [
                "/usr/bin/sips",
                "-s",
                "format",
                "png",
                "-z",
                str(px),
                str(px),
                str(source_png),
                "--out",
                str(dest),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    subprocess.run(
        ["/usr/bin/iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_icns)],
        check=True,
    )
    shutil.rmtree(iconset_dir, ignore_errors=True)
    print(f"[Icon] Built macOS icon bundle -> {output_icns}")


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    svg_path = ICON_DIR / "ai_blackmarker_icon.svg"
    png_path = ICON_DIR / "ai_blackmarker_icon.png"
    icns_path = ICON_DIR / "AppIcon.icns"

    svg_path.write_text(HIG_SVG, encoding="utf-8")
    shutil.copy2(svg_path, STATIC_DIR / "icon.svg")
    print(f"[Icon] Wrote Apple HIG SVG -> {svg_path}")

    render_hig_macos_png(png_path)
    shutil.copy2(png_path, STATIC_DIR / "icon.png")
    build_icns_from_png(png_path, icns_path)


if __name__ == "__main__":
    main()
