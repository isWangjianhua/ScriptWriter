from __future__ import annotations

import argparse
import os

from scriptwriter.rag import rebuild_knowledge_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild Milvus vectors from persisted RAG sources"
    )
    parser.add_argument("--user-id", required=True, help="Tenant user id")
    parser.add_argument("--project-id", required=True, help="Tenant project id")
    parser.add_argument("--doc-id", help="Optional doc_id for incremental rebuild")
    parser.add_argument(
        "--data-dir",
        help="Override RAG data directory containing metadata.db and sources/",
    )
    parser.add_argument("--chunk-max-chars", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.data_dir:
        os.environ["SCRIPTWRITER_RAG_DATA_DIR"] = args.data_dir

    result = rebuild_knowledge_index(
        user_id=args.user_id,
        project_id=args.project_id,
        doc_id=args.doc_id,
        chunk_max_chars=args.chunk_max_chars,
        chunk_overlap=args.chunk_overlap,
    )

    print(
        "rebuild completed:",
        f"docs_processed={result.docs_processed}",
        f"chunks_indexed={result.chunks_indexed}",
        f"deleted_vectors={result.deleted_vectors}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
