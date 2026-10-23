import AppKit
import Foundation
import PDFKit
import Vision

/// Native macOS PDFKit + Apple Vision (`VNRecognizeTextRequest`) reader.
/// Borrowed from DigUp's native macOS reader architecture:
/// Pages with digital text use zero-cost stream extraction, while flattened or scanned
/// pages (< 20 characters) run on the Apple Neural Engine to produce exact PDF-point
/// bounding boxes (`x0, y0, x1, y1` with bottom-left origin).
public enum VisionOCRReader {
    public static func extractScannedPageSpans(from pdfURL: URL) -> [VisionOCRSpan] {
        guard let pdfDoc = PDFDocument(url: pdfURL) else {
            return []
        }

        var spans: [VisionOCRSpan] = []
        let pageCount = pdfDoc.pageCount

        for idx in 0..<pageCount {
            guard let page = pdfDoc.page(at: idx) else { continue }
            let digitalText = (page.string ?? "").trimmingCharacters(in: .whitespacesAndNewlines)

            // Only invoke Vision OCR when the page is a flattened scan or has sparse text
            if digitalText.count >= 40 {
                continue
            }

            let mediaBox = page.bounds(for: .mediaBox)
            guard mediaBox.width > 0, mediaBox.height > 0 else { continue }

            guard let cgImage = renderPageToCGImage(page: page, mediaBox: mediaBox, scale: 2.0) else {
                continue
            }

            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continue
            }

            guard let observations = request.results else { continue }
            for observation in observations {
                guard let topCandidate = observation.topCandidates(1).first else { continue }
                let text = topCandidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
                if text.isEmpty { continue }

                // Vision normalized boundingBox has origin at bottom-left, matching PDFKit & RedactGov!
                let normBox = observation.boundingBox
                let x0 = Double(normBox.minX * mediaBox.width)
                let y0 = Double(normBox.minY * mediaBox.height)
                let x1 = Double(normBox.maxX * mediaBox.width)
                let y1 = Double(normBox.maxY * mediaBox.height)

                spans.append(
                    VisionOCRSpan(
                        page: idx + 1,
                        text: text,
                        x0: (x0 * 100).rounded() / 100,
                        y0: (y0 * 100).rounded() / 100,
                        x1: (x1 * 100).rounded() / 100,
                        y1: (y1 * 100).rounded() / 100
                    )
                )
            }
        }

        return spans
    }

    private static func renderPageToCGImage(
        page: PDFPage,
        mediaBox: CGRect,
        scale: CGFloat
    ) -> CGImage? {
        let width = Int(mediaBox.width * scale)
        let height = Int(mediaBox.height * scale)
        guard width > 0, height > 0 else { return nil }

        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return nil
        }

        context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        context.scaleBy(x: scale, y: scale)
        page.draw(with: .mediaBox, to: context)
        return context.makeImage()
    }
}
