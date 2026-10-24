import AppKit
import PDFKit
import QuartzCore
import RedactGovKit
import SwiftUI

/// Custom PDFView subclass supporting interactive Manual Blackmarker marquee drawing
/// and click-to-select statutory redaction boxes.
public final class BlackmarkerPDFView: PDFView {
    public var isManualDrawMode: Bool = false {
        didSet {
            window?.invalidateCursorRects(for: self)
        }
    }
    public var entities: [RedactionEntityItem] = []
    public var onSelectEntity: ((String) -> Void)?
    public var onManualBoxDrawn: ((Int, CGRect, String?) -> Void)?

    private var dragStartViewPoint: NSPoint?
    private var dragCurrentViewPoint: NSPoint?
    private var dragTargetPage: PDFPage?
    private let marqueeLayer = CAShapeLayer()

    override public init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setupMarqueeLayer()
    }

    required public init?(coder: NSCoder) {
        super.init(coder: coder)
        setupMarqueeLayer()
    }

    private func setupMarqueeLayer() {
        wantsLayer = true
        marqueeLayer.fillColor = NSColor(calibratedRed: 0.05, green: 0.07, blue: 0.11, alpha: 0.55).cgColor
        marqueeLayer.strokeColor = NSColor(calibratedRed: 0.22, green: 0.74, blue: 0.98, alpha: 0.98).cgColor
        marqueeLayer.lineWidth = 2.0
        marqueeLayer.lineDashPattern = [6, 4]
        marqueeLayer.isHidden = true
        layer?.addSublayer(marqueeLayer)
    }

    override public func resetCursorRects() {
        super.resetCursorRects()
        addCursorRect(bounds, cursor: .crosshair)
    }

    override public func mouseDown(with event: NSEvent) {
        let viewPoint = convert(event.locationInWindow, from: nil)
        guard let page = page(for: viewPoint, nearest: true) else {
            super.mouseDown(with: event)
            return
        }
        dragStartViewPoint = viewPoint
        dragCurrentViewPoint = viewPoint
        dragTargetPage = page
        updateMarqueeLayer()
    }

    override public func mouseDragged(with event: NSEvent) {
        guard dragStartViewPoint != nil else {
            super.mouseDragged(with: event)
            return
        }
        dragCurrentViewPoint = convert(event.locationInWindow, from: nil)
        updateMarqueeLayer()
    }

    override public func mouseUp(with event: NSEvent) {
        guard let startPt = dragStartViewPoint,
              let page = dragTargetPage,
              let doc = document else {
            super.mouseUp(with: event)
            return
        }

        let endPt = convert(event.locationInWindow, from: nil)
        dragStartViewPoint = nil
        dragCurrentViewPoint = nil
        dragTargetPage = nil
        marqueeLayer.isHidden = true

        let viewRect = CGRect(
            x: min(startPt.x, endPt.x),
            y: min(startPt.y, endPt.y),
            width: abs(endPt.x - startPt.x),
            height: abs(endPt.y - startPt.y)
        )

        if viewRect.width < 6.0 && viewRect.height < 6.0 {
            // Simple click: check if click landed on an existing redaction entity box
            let pagePoint = convert(endPt, to: page)
            let pageNumber = doc.index(for: page) + 1
            for entity in entities where entity.pageNumber == pageNumber {
                for bbox in entity.boundingBoxes {
                    let rect = CGRect(
                        x: bbox.x0 - 3.0,
                        y: bbox.y0 - 3.0,
                        width: max(8.0, bbox.width + 6.0),
                        height: max(8.0, bbox.height + 6.0)
                    )
                    if rect.contains(pagePoint) {
                        onSelectEntity?(entity.id)
                        return
                    }
                }
            }
            super.mouseUp(with: event)
            return
        }

        guard viewRect.width >= 6.0, viewRect.height >= 6.0 else {
            return
        }

        let pdfRect = convert(viewRect, to: page).standardized
        guard pdfRect.width >= 4.0, pdfRect.height >= 4.0 else {
            return
        }

        let pageNumber = doc.index(for: page) + 1
        let extractedText = page.selection(for: pdfRect)?.string?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        onManualBoxDrawn?(pageNumber, pdfRect, extractedText)
    }

    private func updateMarqueeLayer() {
        guard let start = dragStartViewPoint, let current = dragCurrentViewPoint else {
            marqueeLayer.isHidden = true
            return
        }
        let rect = CGRect(
            x: min(start.x, current.x),
            y: min(start.y, current.y),
            width: abs(current.x - start.x),
            height: abs(current.y - start.y)
        )
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        marqueeLayer.path = CGPath(roundedRect: rect, cornerWidth: 4, cornerHeight: 4, transform: nil)
        marqueeLayer.isHidden = false
        CATransaction.commit()
    }
}

/// Native macOS PDFKit view with high-contrast Section 508 statutory redaction overlays
/// and interactive manual Blackmarker marquee drawing.
public struct PDFKitCanvasView: NSViewRepresentable {
    public let pdfURL: URL?
    public let entities: [RedactionEntityItem]
    public let selectedEntityID: String?
    public let showAnnotations: Bool
    public let isManualDrawMode: Bool
    public let onSelectEntity: ((String) -> Void)?
    public let onManualBoxDrawn: ((Int, CGRect, String?) -> Void)?

    public init(
        pdfURL: URL?,
        entities: [RedactionEntityItem],
        selectedEntityID: String?,
        showAnnotations: Bool = true,
        isManualDrawMode: Bool = false,
        onSelectEntity: ((String) -> Void)? = nil,
        onManualBoxDrawn: ((Int, CGRect, String?) -> Void)? = nil
    ) {
        self.pdfURL = pdfURL
        self.entities = entities
        self.selectedEntityID = selectedEntityID
        self.showAnnotations = showAnnotations
        self.isManualDrawMode = isManualDrawMode
        self.onSelectEntity = onSelectEntity
        self.onManualBoxDrawn = onManualBoxDrawn
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    public func makeNSView(context: Context) -> BlackmarkerPDFView {
        let pdfView = BlackmarkerPDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.displaysPageBreaks = true
        pdfView.backgroundColor = NSColor(calibratedWhite: 0.11, alpha: 1.0)
        return pdfView
    }

    public func updateNSView(_ pdfView: BlackmarkerPDFView, context: Context) {
        pdfView.isManualDrawMode = isManualDrawMode
        pdfView.entities = entities
        pdfView.onSelectEntity = onSelectEntity
        pdfView.onManualBoxDrawn = onManualBoxDrawn

        guard let pdfURL else {
            pdfView.document = nil
            context.coordinator.loadedURL = nil
            return
        }

        if context.coordinator.loadedURL != pdfURL {
            pdfView.document = PDFDocument(url: pdfURL)
            context.coordinator.loadedURL = pdfURL
        }

        guard let document = pdfView.document else { return }

        // Remove previous overlay annotations
        for pageIndex in 0..<document.pageCount {
            guard let page = document.page(at: pageIndex) else { continue }
            let existing = page.annotations.filter { $0.userName == "AIBlackmarkerOverlay" }
            for annot in existing {
                page.removeAnnotation(annot)
            }
        }

        guard showAnnotations else { return }

        var focusPage: PDFPage?
        var focusRect: CGRect?

        for entity in entities {
            let isSelected = (entity.id == selectedEntityID)
            let isManual = (entity.tier == "manual_blackmarker" || entity.category == "manual_redaction")

            for bbox in entity.boundingBoxes {
                let pageIdx = max(0, bbox.page - 1)
                guard pageIdx < document.pageCount, let page = document.page(at: pageIdx) else {
                    continue
                }

                let rect = CGRect(
                    x: bbox.x0 - 1.5,
                    y: bbox.y0 - 1.5,
                    width: max(8.0, bbox.width + 3.0),
                    height: max(8.0, bbox.height + 3.0)
                )

                let annotation = PDFAnnotation(bounds: rect, forType: .square, withProperties: nil)
                annotation.userName = "AIBlackmarkerOverlay"
                annotation.contents = "\(entity.statuteCode) • \(entity.category.uppercased()) • \(entity.text)"

                let border = PDFBorder()
                border.lineWidth = isSelected ? 2.8 : 1.6
                if !entity.approved {
                    border.style = .dashed
                }
                annotation.border = border

                if isSelected {
                    annotation.color = NSColor(calibratedRed: 0.22, green: 0.78, blue: 1.0, alpha: 0.98)
                    annotation.interiorColor = NSColor(calibratedRed: 0.08, green: 0.10, blue: 0.14, alpha: 0.48)
                    focusPage = page
                    focusRect = rect
                } else if entity.approved {
                    if isManual {
                        // Manual Blackmarker boxes get a distinct obsidian + electric blue border
                        annotation.color = NSColor(calibratedRed: 0.22, green: 0.74, blue: 0.98, alpha: 0.95)
                        annotation.interiorColor = NSColor(calibratedRed: 0.05, green: 0.07, blue: 0.10, alpha: 0.45)
                    } else {
                        annotation.color = NSColor(calibratedRed: 0.95, green: 0.24, blue: 0.28, alpha: 0.95)
                        annotation.interiorColor = NSColor(calibratedRed: 0.90, green: 0.14, blue: 0.18, alpha: 0.26)
                    }
                } else {
                    annotation.color = NSColor(calibratedWhite: 0.55, alpha: 0.75)
                    annotation.interiorColor = NSColor(calibratedWhite: 0.50, alpha: 0.10)
                }

                page.addAnnotation(annotation)
            }
        }

        if let focusPage, let focusRect, context.coordinator.lastFocusedEntityID != selectedEntityID {
            context.coordinator.lastFocusedEntityID = selectedEntityID
            pdfView.go(to: focusRect, on: focusPage)
        }
    }

    public final class Coordinator {
        var loadedURL: URL?
        var lastFocusedEntityID: String?
    }
}
