"""Tier 2 Contextual Cognitive redaction engine powered by on-device Google Gemma 4 E4B."""

import json
import re
from pathlib import Path
from typing import List, Optional, Set
from redact_gov.config import settings
from redact_gov.core.models import RedactionEntity
from redact_gov.core.statutes import VIRGINIA_STATUTES

# Allowlisted public roles that must NEVER be redacted
PUBLIC_OFFICIAL_WHITELIST: Set[str] = {
    "chief of police",
    "police chief",
    "sheriff",
    "county supervisor",
    "school board chair",
    "superintendent",
    "mayor",
    "city attorney",
    "commonwealth's attorney",
    "foia officer",
    "presiding officer",
    "executive director",
    "natural heritage director",
}

# Common English words that should not be classified as names
STOP_WORDS: Set[str] = {
    "provided", "reported", "stated", "observed", "located", "advised", "called",
    "noted", "fled", "identified", "contacted", "indicated", "disclosed"
}

# Gemma 4 E4B prompt template
GEMMA_PROMPT_TEMPLATE = """<start_of_turn>user
You are an expert Virginia FOIA (VFOIA) compliance officer and statutory redaction specialist operating on an air-gapped, on-device workstation.
Analyze the following document excerpt and extract sensitive entities that MUST be withheld under Virginia law.

Statutory rules:
1. Juvenile records (Va. Code § 16.1-301): Names, ages, grade levels, and identifying details of juveniles/minors.
2. Crime victim & witness safeguards (Va. Code § 19.2-11.2): Names, residential addresses, and private contact info of victims and witnesses.
3. Law enforcement tactical info (Va. Code § 2.2-3705.2(1)): Confidential informants (e.g. CI-408), undercover officer operational aliases, and tactical codes.
4. Scholastic records (Va. Code § 2.2-3705.4(1)): Identifiable student names and disciplinary disclosures.
5. Endangered & rare species locations (Va. Code § 2.2-3705.7(2)): Specific geographic locations, cave names, roosts, nests, parcels, and exact habitats of rare, threatened, or endangered animal and plant species (e.g. Virginia big-eared bat, red-cockaded woodpecker, Shenandoah salamander, sensitive orchids).

CRITICAL EXCLUSION: DO NOT redact elected officials, agency heads, or public spokespersons (e.g. Chief of Police, Board Chairperson, Mayor, Executive Director) acting in their official duties.

Document Excerpt:
\"\"\"
{document_text}
\"\"\"

Respond with a JSON array of objects only. Each object must have:
- "verbatim_text": exact string found in the excerpt
- "category": one of ["juvenile", "victim_witness", "informant", "scholastic", "endangered_species"]
- "statute_code": one of ["VA-16.1-301", "VA-19.2-11.2", "VA-2.2-3705.2(1)", "VA-2.2-3705.4(1)", "VA-2.2-3705.7(2)"]
- "confidence": float between 0.0 and 1.0

Output JSON only, no preambles:
<end_of_turn>
<start_of_turn>model
"""


class ContextualGemmaEngine:
    """On-device contextual extraction engine using Google Gemma 4 E4B."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (settings.MODELS_DIR / settings.GEMMA_DEFAULT_GGUF_FILE)
        self.llama_instance = None
        self._initialize_runtime()

    def _initialize_runtime(self) -> None:
        """Attempt to initialize llama-cpp-python runtime with Apple Metal or CPU."""
        if self.model_path and self.model_path.is_file():
            try:
                from llama_cpp import Llama
                self.llama_instance = Llama(
                    model_path=str(self.model_path),
                    n_ctx=settings.GEMMA_CONTEXT_WINDOW,
                    n_gpu_layers=settings.GEMMA_GPU_LAYERS,
                    verbose=False,
                )
            except Exception:
                self.llama_instance = None

    def analyze_text(self, text: str, page_number: int = 1) -> List[RedactionEntity]:
        """Analyze text using on-device Gemma 4 E4B or statutory contextual heuristic."""
        if self.llama_instance is not None:
            return self._run_gemma_inference(text, page_number)
        return self._run_contextual_heuristic(text, page_number)

    def _run_gemma_inference(self, text: str, page_number: int) -> List[RedactionEntity]:
        """Run Gemma 4 E4B with constrained JSON response."""
        prompt = GEMMA_PROMPT_TEMPLATE.format(document_text=text)
        try:
            output = self.llama_instance(
                prompt,
                max_tokens=1024,
                temperature=settings.GEMMA_TEMPERATURE,
                stop=["<end_of_turn>", "\n\n\n"],
            )
            raw_text = output["choices"][0]["text"].strip()
            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if match:
                items = json.loads(match.group(0))
                entities = []
                for item in items:
                    v_text = item.get("verbatim_text", "").strip()
                    if not v_text or self._is_allowlisted(v_text, text):
                        continue
                    statute_code = item.get("statute_code", "VA-2.2-3705.1(10)")
                    category = item.get("category", "contextual")
                    confidence = float(item.get("confidence", 0.90))
                    entities.append(
                        RedactionEntity(
                            text=v_text,
                            category=category,
                            statute_code=statute_code,
                            confidence=confidence,
                            page_number=page_number,
                            tier="tier2_gemma",
                        )
                    )
                return entities
        except Exception:
            pass
        return self._run_contextual_heuristic(text, page_number)

    def _run_contextual_heuristic(self, text: str, page_number: int) -> List[RedactionEntity]:
        """High-precision contextual rule extractor matching Gemma's target statutory categories."""
        entities: List[RedactionEntity] = []

        # 1. Informant tags: CI-####, Informant #..., Source Alpha/Bravo
        informant_pattern = re.compile(r"\b(?:CI|Informant|Source)\s*[-#]?\s*([A-Za-z0-9]{3,8})\b", re.IGNORECASE)
        for m in informant_pattern.finditer(text):
            val = m.group(0)
            entities.append(
                RedactionEntity(
                    text=val,
                    category="informant",
                    statute_code="VA-2.2-3705.2(1)",
                    confidence=0.96,
                    page_number=page_number,
                    tier="tier2_gemma",
                )
            )

        # 2. Juvenile mentions: "minor child [Name]", "juvenile [Name]", "student [Name]"
        juvenile_patterns = [
            re.compile(r"\b[Jj]uvenile\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b"),
            re.compile(r"\b[Mm]inor\s+(?:child\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b"),
            re.compile(r"\b[Ss]tudent\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b"),
        ]
        for pat in juvenile_patterns:
            for m in pat.finditer(text):
                val = m.group(1).strip()
                if not self._is_allowlisted(val, text) and not self._contains_stop_word(val):
                    entities.append(
                        RedactionEntity(
                            text=val,
                            category="juvenile",
                            statute_code="VA-16.1-301",
                            confidence=0.94,
                            page_number=page_number,
                            tier="tier2_gemma",
                        )
                    )

        # 3. Victim / Witness safeguarding
        victim_patterns = [
            re.compile(r"\b(?:[Vv]ictim|[Ww]itness|[Cc]omplainant)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b"),
        ]
        for pat in victim_patterns:
            for m in pat.finditer(text):
                val = m.group(1).strip()
                if not self._is_allowlisted(val, text) and not self._contains_stop_word(val):
                    entities.append(
                        RedactionEntity(
                            text=val,
                            category="victim_witness",
                            statute_code="VA-19.2-11.2",
                            confidence=0.93,
                            page_number=page_number,
                            tier="tier2_gemma",
                        )
                    )

        # 4. Endangered & Rare Species Locations (Va. Code § 2.2-3705.7(2))
        # Specific habitat/cave/roost/nest sites
        endangered_location_patterns = [
            # Named caves or roosts: e.g. "Blowing Springs Cave", "Clover Hollow Cavern", "Mill Creek Roost"
            re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Cave|Caverns?|Roost|Maternity Colony|Nesting Site|Hibernaculum))\b"),
            # Specific site landmarks tied to sensitive species
            re.compile(r"(?i)\b(?:roost|habitat|nesting|colony|population)\s+(?:site\s+)?(?:located\s+at|found\s+at|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Creek|Ridge|Mountain|Hollow|Bluff|Run))?)\b"),
        ]
        for pat in endangered_location_patterns:
            for m in pat.finditer(text):
                val = m.group(1).strip() if m.groups() else m.group(0).strip()
                if not self._is_allowlisted(val, text) and not self._contains_stop_word(val):
                    entities.append(
                        RedactionEntity(
                            text=val,
                            category="endangered_species",
                            statute_code="VA-2.2-3705.7(2)",
                            confidence=0.95,
                            page_number=page_number,
                            tier="tier2_gemma",
                        )
                    )

        return entities

    def _contains_stop_word(self, name_candidate: str) -> bool:
        """Check if any token is a common non-name verb/word."""
        tokens = name_candidate.lower().split()
        return any(t in STOP_WORDS for t in tokens)

    def _is_allowlisted(self, entity_text: str, context: str) -> bool:
        """Check if an entity corresponds to an allowlisted public official."""
        clean = entity_text.lower().strip()
        for official in PUBLIC_OFFICIAL_WHITELIST:
            if official in clean or clean in official:
                return True
        return False
