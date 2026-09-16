import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from redact_gov.engines.contextual import ContextualGemmaEngine
from redact_gov.pipeline import RedactionPipeline
import pdfplumber

def test_contextual_engine_vision_fallback(tmp_path):
    engine = ContextualGemmaEngine(model_path=Path("nonexistent.gguf"), mmproj_path=Path("nonexistent.gguf"))
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"dummy image content")
    
    entities = engine.analyze_image(img_path, page_number=1)
    
    assert len(entities) == 2
    assert entities[0].category == "signature"
    assert entities[1].category == "handwritten"
    assert entities[0].bounding_boxes[0].y0 == 600.0

@patch("redact_gov.pipeline.pdfplumber.open")
@patch("redact_gov.pipeline.pikepdf.open")
def test_pipeline_scanned_page_detection(mock_pikepdf, mock_pdfplumber, tmp_path):
    # Setup mock PDF with one scanned page (empty text) and one text page
    mock_pdf = MagicMock()
    
    # Page 1: Scanned (no text)
    page1 = MagicMock()
    page1.extract_text.return_value = "   " # Length < 20
    
    mock_image = MagicMock()
    page1.to_image.return_value.original = mock_image
    
    # Page 2: Text page
    page2 = MagicMock()
    page2.extract_text.return_value = "This is a normal page with text more than 20 characters."
    
    mock_pdf.pages = [page1, page2]
    mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
    
    mock_pike = MagicMock()
    mock_pike.pages = [MagicMock(), MagicMock()]
    mock_pikepdf.return_value.__enter__.return_value = mock_pike
    
    pipeline = RedactionPipeline()
    
    # We patch analyze_image to know it was called
    with patch.object(pipeline.contextual_engine, "analyze_image") as mock_analyze_img:
        mock_analyze_img.return_value = []
        
        with patch.object(pipeline.contextual_engine, "analyze_text") as mock_analyze_txt:
            mock_analyze_txt.return_value = []
            
            dummy_pdf = tmp_path / "dummy.pdf"
            dummy_pdf.touch()
            
            # mock get_document_page_count
            with patch("redact_gov.pipeline.get_document_page_count", return_value=2):
                pipeline.create_plan(dummy_pdf, normalize_imperfect=False)
                
                # Assert analyze_image called for page 1
                assert mock_analyze_img.called
                assert mock_analyze_img.call_args[1]["page_number"] == 1
                
                # Assert analyze_text called for page 2
                assert mock_analyze_txt.called
                assert mock_analyze_txt.call_args[1]["page_number"] == 2
