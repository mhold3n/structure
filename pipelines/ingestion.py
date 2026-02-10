import os
import json
import hashlib
import uuid
import shutil
from datetime import datetime, timezone
from typing import List, Optional, Set

from pipelines.contracts import PipelineStage, PipelineContext
from schemas.ingest.contracts import (
    Document, Provenance, Partition, License
)

# Constants
INDEX_ROOT = "indexes"
MANIFEST_PATH = "ingest/manifest.jsonl"


class RawImportStage(PipelineStage[dict, Document]):
    """
    Stage 1: Validates raw input and creates a canonical Document object.
    """
    def run(self, input_data: dict) -> Document:
        content = input_data.get("content")
        source_name = input_data.get("source_name")
        source_path = input_data.get("source_path")
        license_str = input_data.get("license", "Unknown")
        
        # Validation happens here via Pydantic
        if not content:
            raise ValueError("Content is required")

        doc_hash = hashlib.md5(content.encode()).hexdigest()
        
        provenance = Provenance(
            source_name=source_name,
            source_uri=source_path,
            author=input_data.get("author"),
            date_acquired=datetime.now(timezone.utc),
            license=License(license_str) if license_str in License.__members__.values() else License.UNKNOWN,
            ingestion_id=self.context.run_id
        )

        return Document(
            content=content,
            content_hash=doc_hash,
            provenance=provenance,
            metadata={"raw_import": True}
        )


class DeduplicationStage(PipelineStage[Document, Optional[Document]]):
    """
    Stage 2: Checks for duplicates against a test index.
    """
    def __init__(self, context: PipelineContext):
        super().__init__(context)
        self.test_hashes = self._load_test_hashes()

    def _load_test_hashes(self) -> Set[str]:
        # Minimal implementation: Load hashes from a specific test index directory
        # In a real system, this might query a vector DB or global index
        hashes = set()
        test_index_path = os.path.join(INDEX_ROOT, "test")
        if os.path.exists(test_index_path):
            for root, _, files in os.walk(test_index_path):
                for file in files:
                    if file.endswith(".json"):
                        try:
                            with open(os.path.join(root, file), "r") as f:
                                data = json.load(f)
                                if "content_hash" in data:
                                    hashes.add(data["content_hash"])
                        except Exception:
                            pass
        return hashes

    def run(self, doc: Document) -> Optional[Document]:
        if doc.content_hash in self.test_hashes:
            print(f"REJECTED: Document content matches Test index. Hash: {doc.content_hash}")
            return None
        return doc


class PartitioningStage(PipelineStage[Document, Document]):
    """
    Stage 3: Assigns data to Train/Dev/Test partitions.
    """
    def run(self, doc: Document) -> Document:
        # Deterministic partitioning based on content hash
        # Strategy:
        # 00-7f (50%) -> Train
        # 80-bf (25%) -> Dev
        # c0-ff (25%) -> Test
        
        # However, if we want to enforce that "Test" is held-out and possibly
        # manually curated, we might want a different rule or input flag.
        # For this implementation, we'll use a deterministic hash rule 
        # unless overridden.
        
        first_byte = int(doc.content_hash[:2], 16)
        
        if first_byte < 128: # 00-7F
            doc.partition = Partition.TRAIN
        elif first_byte < 192: # 80-BF
            doc.partition = Partition.DEV
        else: # C0-FF
            doc.partition = Partition.TEST
            
        return doc


class PersistenceStage(PipelineStage[Document, Document]):
    """
    Stage 4: Writes the document to disk and manifest.
    """
    def run(self, doc: Document) -> Document:
        if self.context.dry_run:
            print(f"[DRY RUN] Would write doc {doc.id} to {doc.partition}")
            return doc

        # 1. Write to Partition Directory
        # Structure: indexes/{partition}/documents/{doc_id}.json
        output_dir = os.path.join(INDEX_ROOT, doc.partition.value, "documents")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{doc.id}.json")
        with open(output_path, "w") as f:
            f.write(doc.model_dump_json(indent=2))
            
        # 2. Append to Manifest
        self._log_to_manifest(doc)
        
        return doc

    def _log_to_manifest(self, doc: Document):
        os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
        with open(MANIFEST_PATH, "a") as f:
            # Minified JSON for log
            f.write(doc.model_dump_json() + "\n")


class IngestionPipeline:
    def __init__(self, dry_run: bool = False):
        self.context = PipelineContext(
            run_id=str(uuid.uuid4()),
            dry_run=dry_run
        )
        
        # Initialize Stages
        self.raw_import = RawImportStage(self.context)
        self.dedup = DeduplicationStage(self.context)
        self.partition = PartitioningStage(self.context)
        self.persistence = PersistenceStage(self.context)

    def ingest(self, input_payload: dict) -> Optional[Document]:
        """
        Run the ingestion DAG.
        """
        try:
            # Stage 1: Import
            doc = self.raw_import.run(input_payload)
            
            # Stage 2: Dedup
            doc = self.dedup.run(doc)
            if not doc:
                return None # Duplicate rejected
            
            # Stage 3: Partition
            doc = self.partition.run(doc)
            
            # Stage 4: Persist
            doc = self.persistence.run(doc)
            
            print(f"SUCCESS: Ingested document {doc.id} into {doc.partition.value}")
            return doc
            
        except Exception as e:
            print(f"INGESTION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None


def demo_ingestion():
    pipeline = IngestionPipeline(dry_run=False)

    # Valid Ingestion
    payload = {
        "content": "This is authoritative text from a physics textbook.",
        "source_name": "OpenStax_Physics",
        "license": "CC-BY",
        "source_path": "/raw/physics_vol1.pdf",
        "author": "OpenStax",
    }
    
    pipeline.ingest(payload)


if __name__ == "__main__":
    demo_ingestion()
