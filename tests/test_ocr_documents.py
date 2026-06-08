from pathlib import Path


def test_generate_ocr_documents_creates_manifest_and_assets(tmp_path, monkeypatch):
    from data.synthetic import generate_ocr_documents as god

    output_dir = tmp_path / "ocr_documents"
    manifest_path = output_dir / "manifest.jsonl"

    monkeypatch.setattr(god, "DEFAULT_CONN", None)
    monkeypatch.setattr(god, "DEFAULT_CONTAINER", "argus-ocr-docs")
    monkeypatch.setattr(god, "DEFAULT_PREFIX", "ocr-documents")

    factory = god.DocFactory(output_dir=output_dir, seed=20260608)
    records = factory.create_documents()

    # Full matrix: 4 doc types × 6 quality levels × (PNG + PDF if reportlab available)
    assert len(records) >= 4 * len(god.QUALITY_STYLES)
    all_qualities = {r.quality for r in records}
    assert all_qualities == set(god.QUALITY_STYLES.keys())
    all_types = {r.doc_type for r in records}
    assert all_types == set(god.DOC_TYPES)
    assert any(r.format == "png" for r in records)

    god.write_manifest(records, manifest_path)

    assert manifest_path.exists()
    manifest_lines = [line for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(manifest_lines) == len(records)

    created_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    assert any(name.endswith(".png") for name in created_files)

    first = records[0]
    assert first.doc_type in god.DOC_TYPES
    assert first.ground_truth
    assert first.blob_name.startswith("ocr-documents/")


def test_upload_documents_uses_blob_urls(monkeypatch, tmp_path):
    from data.synthetic import generate_ocr_documents as god

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"png-bytes")
    record = god.OCRDocument(
        doc_id="sample",
        doc_type="passport",
        layout="passport_clean",
        quality="clean",
        format="png",
        file_name="sample.png",
        local_path=str(sample),
        blob_name="ocr-documents/sample.png",
        blob_url=None,
        entity_name="Jane Example",
        entity_type="individual",
        jurisdiction="DE",
        ground_truth={"full_name": "Jane Example"},
    )

    class FakeBlobClient:
        def __init__(self, url):
            self.url = url
            self.uploaded = False

        def upload_blob(self, handle, overwrite=True, content_settings=None):
            self.uploaded = True
            assert handle.read() == b"png-bytes"

    class FakeContainer:
        def __init__(self):
            self.blob = FakeBlobClient("https://example.blob.core.windows.net/container/ocr-documents/sample.png")

        def create_container(self):
            return None

        def get_blob_client(self, name):
            assert name == record.blob_name
            return self.blob

    class FakeService:
        def get_container_client(self, name):
            assert name == "argus-ocr-docs"
            return FakeContainer()

    class FakeBlobServiceClient:
        @staticmethod
        def from_connection_string(connection_string):
            assert connection_string == "UseDevelopmentStorage=true"
            return FakeService()

    monkeypatch.setattr("azure.storage.blob.BlobServiceClient", FakeBlobServiceClient)

    uploaded = god.upload_documents([record], "UseDevelopmentStorage=true", "argus-ocr-docs")
    assert uploaded[0].blob_url.startswith("https://example.blob.core.windows.net/")
