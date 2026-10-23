import Foundation
import SQLite3

/// Local SQLite docket & redaction memory index (modeled after DigUp's SQLite index store).
/// Indexes every sanitized document, withheld entity, and Virginia Code statutory citation
/// so clerks can query across an entire multi-PDF FOIA release docket on-device.
public final class CaseIndexStore: @unchecked Sendable {
    private var db: OpaquePointer?
    private let lock = NSLock()
    public let databasePath: String

    public init(databaseURL: URL? = nil) {
        let resolvedURL: URL
        if let databaseURL {
            resolvedURL = databaseURL
        } else {
            let appSupport = FileManager.default.urls(
                for: .applicationSupportDirectory,
                in: .userDomainMask
            ).first ?? URL(fileURLWithPath: NSTemporaryDirectory())
            let folder = appSupport.appendingPathComponent("RedactGov", isDirectory: true)
            try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            resolvedURL = folder.appendingPathComponent("foia_docket_index.sqlite3")
        }

        self.databasePath = resolvedURL.path
        openAndMigrate()
    }

    deinit {
        if let db {
            sqlite3_close(db)
        }
    }

    private func openAndMigrate() {
        lock.lock()
        defer { lock.unlock() }

        if sqlite3_open(databasePath, &db) != SQLITE_OK {
            return
        }

        let schemaSQL = """
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS docket_redactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT NOT NULL,
            output_path TEXT NOT NULL,
            certificate_path TEXT,
            entity_text TEXT NOT NULL,
            category TEXT NOT NULL,
            statute_code TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            verified_zero_residual INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_docket_statute ON docket_redactions(statute_code);
        CREATE INDEX IF NOT EXISTS idx_docket_doc ON docket_redactions(document_name);
        """
        sqlite3_exec(db, schemaSQL, nil, nil, nil)
    }

    public func recordRedactionRun(
        plan: RedactionPlanPayload,
        result: RedactionResultPayload
    ) {
        lock.lock()
        defer { lock.unlock() }
        guard let db else { return }

        let insertSQL = """
        INSERT INTO docket_redactions (
            document_name, output_path, certificate_path, entity_text,
            category, statute_code, page_number, verified_zero_residual, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        let now = ISO8601DateFormatter().string(from: Date())
        let sqlTransient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

        for entity in plan.entities where entity.approved {
            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(db, insertSQL, -1, &stmt, nil) == SQLITE_OK else {
                continue
            }
            defer { sqlite3_finalize(stmt) }

            sqlite3_bind_text(stmt, 1, plan.documentName, -1, sqlTransient)
            sqlite3_bind_text(stmt, 2, result.outputPath, -1, sqlTransient)
            if let cert = result.certificatePath {
                sqlite3_bind_text(stmt, 3, cert, -1, sqlTransient)
            } else {
                sqlite3_bind_null(stmt, 3)
            }
            sqlite3_bind_text(stmt, 4, entity.text, -1, sqlTransient)
            sqlite3_bind_text(stmt, 5, entity.category, -1, sqlTransient)
            sqlite3_bind_text(stmt, 6, entity.statuteCode, -1, sqlTransient)
            sqlite3_bind_int(stmt, 7, Int32(entity.pageNumber))
            sqlite3_bind_int(stmt, 8, result.verificationPassed ? 1 : 0)
            sqlite3_bind_text(stmt, 9, now, -1, sqlTransient)

            sqlite3_step(stmt)
        }
    }

    public func searchDocket(query: String, limit: Int = 60) -> [DocketAuditEntry] {
        lock.lock()
        defer { lock.unlock() }
        guard let db else { return [] }

        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let sql: String
        if trimmed.isEmpty {
            sql = """
            SELECT id, document_name, output_path, certificate_path, entity_text,
                   category, statute_code, page_number, verified_zero_residual, created_at
            FROM docket_redactions
            ORDER BY id DESC
            LIMIT ?;
            """
        } else {
            sql = """
            SELECT id, document_name, output_path, certificate_path, entity_text,
                   category, statute_code, page_number, verified_zero_residual, created_at
            FROM docket_redactions
            WHERE document_name LIKE ? OR entity_text LIKE ? OR statute_code LIKE ? OR category LIKE ?
            ORDER BY id DESC
            LIMIT ?;
            """
        }

        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            return []
        }
        defer { sqlite3_finalize(stmt) }

        let sqlTransient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
        if trimmed.isEmpty {
            sqlite3_bind_int(stmt, 1, Int32(limit))
        } else {
            let pattern = "%\(trimmed)%"
            sqlite3_bind_text(stmt, 1, pattern, -1, sqlTransient)
            sqlite3_bind_text(stmt, 2, pattern, -1, sqlTransient)
            sqlite3_bind_text(stmt, 3, pattern, -1, sqlTransient)
            sqlite3_bind_text(stmt, 4, pattern, -1, sqlTransient)
            sqlite3_bind_int(stmt, 5, Int32(limit))
        }

        var entries: [DocketAuditEntry] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = sqlite3_column_int64(stmt, 0)
            let docName = Self.columnText(stmt, 1)
            let outPath = Self.columnText(stmt, 2)
            let certPathRaw = Self.columnText(stmt, 3)
            let entityText = Self.columnText(stmt, 4)
            let category = Self.columnText(stmt, 5)
            let statute = Self.columnText(stmt, 6)
            let page = Int(sqlite3_column_int(stmt, 7))
            let verified = sqlite3_column_int(stmt, 8) == 1
            let createdAt = Self.columnText(stmt, 9)

            entries.append(
                DocketAuditEntry(
                    id: id,
                    documentName: docName,
                    outputPath: outPath,
                    certificatePath: certPathRaw.isEmpty ? nil : certPathRaw,
                    entityText: entityText,
                    category: category,
                    statuteCode: statute,
                    pageNumber: page,
                    verifiedZeroResidual: verified,
                    createdAt: createdAt
                )
            )
        }
        return entries
    }

    private static func columnText(_ stmt: OpaquePointer?, _ index: Int32) -> String {
        guard let cStr = sqlite3_column_text(stmt, index) else { return "" }
        return String(cString: cStr)
    }
}
