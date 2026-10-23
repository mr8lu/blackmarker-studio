"""Configuration settings for Blackmarker Studio sovereign redaction engine."""

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile


SYNTHETIC_DOCUMENTS: list[tuple[str, str, str]] = [
    (
        "police_incident_narrative.pdf",
        "OFFICIAL POLICE DIVISION INCIDENT RECORD",
        """HENRICO COUNTY POLICE DIVISION - INCIDENT & ARREST NARRATIVE
Case Number: 2026-CR-08942
Reporting Officer: Officer Marcus Vance, Badge #412
Approved By: Chief of Police Eric D. Henderson
Date of Incident: August 14, 2026
Location: 4800 Block of West Broad Street, Richmond, VA 23230

INCIDENT NARRATIVE:
On Thursday, August 14, 2026, at approximately 21:40 hours, Unit 412 was dispatched to a commercial property on West Broad Street regarding a disturbance in progress.

Upon arrival, officers contacted complainant Rachel Morrison (DOB: 04/12/1988), who stated an altercation had occurred in the parking lot. Complainant provided her residential phone number (804) 555-0193 and driver's license T48192044.

Witness David Chen was present at the scene and provided eyewitness statements. Witness Chen reported that two juveniles were observed fleeing the premises. Officers subsequently located juvenile Brandon Miller (DOB: 11/03/2010, age 15) and minor child Sophia Miller (age 11) seated near an adjacent convenience store.

Pursuant to operational briefing notes, information regarding the narcotics trafficking investigation in this corridor was originally supplied by confidential informant CI-9140. Tactical code Delta-7 was initiated.

Suspect Arthur Pendelton (SSN: 987-65-4320, DOB: 02/22/1979) was taken into custody without further incident. Chief of Police Eric D. Henderson was briefed via dispatch.

All evidence cataloged under Henrico Police Division General Orders.""",
    ),
    (
        "school_board_disciplinary_record.pdf",
        "SCHOLASTIC DISCIPLINARY PROCEEDING TRANSCRIPT",
        """FAIRFAX COUNTY PUBLIC SCHOOLS - STUDENT DISCIPLINARY COMMITTEE HEARING
Hearing Reference: FCPS-DISC-2026-041
Date: September 02, 2026
Presiding Officer: Superintendent Dr. Karen Reynolds
School Board Chairperson: Jonathan Bradley, Esq.

CONFIDENTIAL SCHOLASTIC RECORD - NOT FOR PUBLIC DISCLOSURE UNDER VA CODE § 2.2-3705.4

RECORD OF PROCEEDINGS:
The Disciplinary Review Committee convened at 14:00 hours at the Gatehouse Administration Center.
Student Subject: Student Tyler Jenkins (Student ID: FC-883921, Grade 10, Date of Birth: 06/18/2010).
Parent / Guardian: Kimberly Jenkins, Residential Address: 1042 Elmwood Terrace, McLean, VA 22101.
Contact Phone: (703) 555-8321. Parent Email: kimberly.jenkins@examplemail.org.

INCIDENT DETAILS:
On August 28, 2026, student Tyler Jenkins was involved in a violation of the FCPS Student Rights and Responsibilities Policy 2601 on school grounds at Langley High School. Student witness Lucas Adams gave testimony regarding possession of prohibited electronic recording devices during a standardized exam.

Counsel for the family submitted medical documentation indicating an individualized education plan (IEP). Parent provided verification with Virginia Driver's License R90218491 and confirmed family SSN records (SSN: 223-45-6789).

Superintendent Dr. Karen Reynolds and School Board Chairperson Jonathan Bradley recommended a 10-day restorative suspension.

Hearing concluded at 15:45 hours.""",
    ),
    (
        "municipal_rezoning_dispute.pdf",
        "MUNICIPAL PLANNING & REZONING PROTEST DOCKET",
        """ALBEMARLE COUNTY BOARD OF SUPERVISORS - PLANNING COMMISSION DISPUTE FILE
Application Number: REZ-2026-0048 (Old Ivy Mixed-Use Proposal)
Public Hearing Date: August 20, 2026
County Supervisor: Supervisor Samuel Vance (Rivanna District)
Planning Director: City Attorney Elena Gomez

FORMAL CITIZEN PROTEST & PETITION DISCLOSURE:
During the public hearing concerning parcel 05800-00-00-014A0, several adjacent property owners filed formal objections alleging stormwater runoff non-compliance.

Citizen Complainant: Evelyn Sinclair
Address: 2840 Fox Ridge Run, Charlottesville, VA 22901
Phone: (434) 555-7729
Email: evelyn.sinclair@privatemail.net
Identity Verification: Virginia Driver's License B11982345
Financial Disclosures: Personal check routing #051000033, Account ending in 4102.

Additional Objector: Robert MacIntyre (SSN: 334-56-7890)
Phone: (434) 555-9012
Complainant MacIntyre submitted proprietary land appraisal evaluations that are exempt under Va. Code § 2.2-3705.6.

Supervisor Samuel Vance acknowledged receipt of citizen grievances and requested an environmental impact assessment from staff. City Attorney Elena Gomez confirmed the review timetable under the Code of Virginia.""",
    ),
    (
        "environmental_impact_assessment.pdf",
        "DCR NATURAL HERITAGE ENVIRONMENTAL REVIEW",
        """COMMONWEALTH OF VIRGINIA - DEPARTMENT OF CONSERVATION AND RECREATION
DIVISION OF NATURAL HERITAGE - ENVIRONMENTAL RESOURCE IMPACT REVIEW
Project File: DCR-NH-2026-0774
Project Title: Jackson River Corridor Scenic Trail & Bridge Rehabilitation
Jurisdiction: Bath County & Highland County, Virginia
Reviewing Authority: Natural Heritage Director Marcus Thornton
Agency Executive: Executive Director Sandra Alvarez

STATUTORY CONFIDENTIALITY NOTICE:
Pursuant to Va. Code § 2.2-3705.7(2), information identifying the specific geographic locations of rare, threatened, or endangered plant or animal species, natural communities, and significant karst/cave resources is strictly protected from public disclosure under the Virginia Freedom of Information Act to prevent unlawful taking and habitat degradation.

SECTION 1: NATURAL HERITAGE SPECIES ASSESSMENT
Field surveys conducted in the upper Jackson River watershed documented critical breeding and hibernation habitats for two federally listed endangered species.

1. Virginia Big-Eared Bat (Corynorhinus townsendii virginianus):
Biologists documented an active summer maternity colony occupying subterranean karst features.
Primary hibernaculum identified at Blowing Springs Cave with a satellite bachelor roost at Clover Hollow Cavern.
Precise cave portal entrance coordinates: 37°58'42.1"N 79°49'15.3"W (Decimal GPS: 37.9782, -79.8194).
Unauthorized human visitation during the active pup-rearing season (May 15 - August 15) poses severe mortality risks from white-nose syndrome disturbance.

2. Small Whorled Pogonia (Isotria medeoloides):
A viable colony of 14 flowering stems of this state and federally threatened orchid was surveyed on an undisturbed acidic ravine slope.
Population located at Mill Creek Bluff on private conservation easement parcel #034-01-09.
Site centroid coordinates: 38°12'14.6"N 79°31'08.2"W.

SECTION 2: AGENCY RECOMMENDATIONS
Executive Director Sandra Alvarez and Natural Heritage Director Marcus Thornton recommend a 500-meter buffer zone precluding all heavy equipment operations around the sensitive cave portals and ravine bluffs. Public release of project documentation must redact all specific cave names, landmark coordinates, and parcel numbers under Va. Code § 2.2-3705.7(2).""",
    ),
]


def _render_synthetic_pdf(raw_content: str, pdf_path: Path, title: str) -> None:
    """Render a synthetic multi-page PDF document via ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

    paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "DocHeader",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
    )

    story = [
        Paragraph(title, header_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#64748b"), spaceAfter=14),
    ]

    for p in paragraphs:
        cleaned = p.replace("&", "&amp;").replace("\n", "<br/>")
        story.append(Paragraph(cleaned, body_style))
        story.append(Spacer(1, 12))

    story.append(PageBreak())
    story.append(Paragraph(f"{title} - Continuation Sheet (Page 2)", header_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#64748b"), spaceAfter=14))
    continuation_note = (
        "CONFIDENTIAL AUDIT TRAIL &amp; AGENCY TRANSMITTAL<br/><br/>"
        "This secondary page serves as formal receipt under Virginia Code § 2.2-3704. "
        "Records custodian notes confirm dispatch logs and intake interviews are held within local division archives. "
        "Direct FOIA inquiries to the Commonwealth Public Information Officer."
    )
    story.append(Paragraph(continuation_note, body_style))
    doc.build(story)


def ensure_synthetic_corpus(synthetic_dir: Path) -> None:
    """Ensure the canonical synthetic PDF corpus exists on disk, generating any missing files."""
    try:
        synthetic_dir.mkdir(parents=True, exist_ok=True)
        for filename, title, raw_text in SYNTHETIC_DOCUMENTS:
            pdf_path = synthetic_dir / filename
            if not pdf_path.is_file():
                _render_synthetic_pdf(raw_text, pdf_path, title)
    except Exception:
        pass


@dataclass
class Settings:
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    SYNTHETIC_DIR: Path = DATA_DIR / "synthetic_corpus"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    MODELS_DIR: Path = PROJECT_ROOT / "models"

    # Google Gemma Configuration (Targeting Google Gemma 4 E4B Edge Model)
    GEMMA_MODEL_NAME: str = "google/gemma-4-e4b-it-GGUF"
    GEMMA_DEFAULT_GGUF_FILE: str = "gemma-4-e4b-it-Q4_K_M.gguf"
    GEMMA_CONTEXT_WINDOW: int = 8192
    GEMMA_TEMPERATURE: float = 0.1
    GEMMA_GPU_LAYERS: int = -1 if os.uname().sysname == "Darwin" else 0  # Metal acceleration on macOS

    # Deterministic engine settings
    ENABLE_DETERMINISTIC_FAST_PATH: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 0.75

    # PikePDF stream surgery settings
    ERADICATE_METADATA: bool = True
    REWRITE_GLYPH_STREAMS: bool = True
    BURN_OPAQUE_POLYGONS: bool = True

    def __post_init__(self) -> None:
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
            self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Fallback to user-writable temp directory if PROJECT_ROOT is read-only
            fallback_root = Path(tempfile.gettempdir()) / "blackmarker_studio"
            self.DATA_DIR = fallback_root / "data"
            self.SYNTHETIC_DIR = self.DATA_DIR / "synthetic_corpus"
            self.OUTPUT_DIR = self.DATA_DIR / "output"
            self.MODELS_DIR = fallback_root / "models"
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
            self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            self.MODELS_DIR.mkdir(parents=True, exist_ok=True)

        ensure_synthetic_corpus(self.SYNTHETIC_DIR)


settings = Settings()
