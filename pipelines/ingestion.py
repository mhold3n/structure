import os
import json
import hashlib
import uuid
from datetime import date
from typing import List, Optional
from models.ingest import Document, Provenance
from schemas.ingest import document  # Import for validation if needed, but we use Pydantic

MANIFEST_PATH = "ingest/manifest.jsonl"
TEST_INDEX_PATH = "indexes/test"


class IngestionPipeline:
    def __init__(self):
        self._ensure_manifest()
        self.test_hashes = self._load_test_hashes()

    def _ensure_manifest(self):
        if not os.path.exists(MANIFEST_PATH):
            with open(MANIFEST_PATH, "w") as f:
                pass

    def _load_test_hashes(self):
        hashes = set()
        if os.path.exists(TEST_INDEX_PATH):
            for root, _, files in os.walk(TEST_INDEX_PATH):
                for file in files:
                    with open(os.path.join(root, file), "rb") as f:
                        hashes.add(hashlib.md5(f.read()).hexdigest())
        return hashes

    def ingest_document(
        self,
        content: str,
        source_name: str,
        license: str,
        source_path: str,
        author: Optional[str] = None,
    ) -> Optional[Document]:
        # 1. Compute Hash
        doc_hash = hashlib.md5(content.encode()).hexdigest()

        # 2. Dedup Gate (Exact)
        if doc_hash in self.test_hashes:
            print(f"REJECTED: Document content matches Test index. Hash: {doc_hash}")
            return None

        # 3. Create Canonical Document
        try:
            doc = Document(
                provenance=Provenance(
                    source_name=source_name, date_acquired=date.today(), author=author
                ),
                license=license,
                source_path=source_path,
                content=content,
                metadata={"hash": doc_hash},
            )
        except ValueError as e:
            print(f"VALIDATION ERROR: {e}")
            return None

        # 4. Write to Manifest
        self._log_to_manifest(doc)

        # 5. Save to Dev/Train path (simulated for now, return doc)
        return doc

    def _log_to_manifest(self, doc: Document):
        with open(MANIFEST_PATH, "a") as f:
            f.write(doc.model_dump_json() + "\n")


def demo_ingestion():
    pipeline = IngestionPipeline()

    # Valid Ingestion
    doc = pipeline.ingest_document(
        content="This is authoritative text from a physics textbook.",
        source_name="OpenStax_Physics",
        license="CC-BY",
        source_path="/raw/physics_vol1.pdf",
        author="OpenStax",
    )

    if doc:
        print(f"SUCCESS: Ingested document {doc.id}")


if __name__ == "__main__":
    demo_ingestion()
