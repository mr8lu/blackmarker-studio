"""RedactGov - Sovereign on-device FOIA redaction engine."""

from redact_gov.core.normalizer import silence_parser_warnings

# Ensure third-party parser noise is silenced across all modules
silence_parser_warnings()


def main() -> None:
    from redact_gov.cli import main as cli_main
    cli_main()

