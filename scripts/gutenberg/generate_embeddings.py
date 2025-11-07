#!/usr/bin/env python3
"""
Generate embeddings for all books in InvenioRDM.

This script:
1. Fetches all records from InvenioRDM
2. Downloads the attached text files
3. Generates embeddings using sentence-transformers
4. Saves embeddings to a JSON file for later indexing
"""

import json
import os
import sys
from pathlib import Path

# Add invenio-aisearch to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "invenio-aisearch"))

import requests
import urllib3
from invenio_aisearch.models import get_model_manager

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EmbeddingGenerator:
    """Generate embeddings for InvenioRDM records."""

    def __init__(
        self,
        base_url: str = "https://127.0.0.1:5000",
        output_file: str = "embeddings.json",
    ):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.output_file = output_file
        self.model_manager = get_model_manager()

    def fetch_all_records(self):
        """Fetch all records from InvenioRDM API."""
        print(f"Fetching records from {self.api_url}/records...")

        all_records = []
        url = f"{self.api_url}/records?size=100"

        while url:
            response = requests.get(url, verify=False)
            response.raise_for_status()

            data = response.json()
            all_records.extend(data['hits']['hits'])

            # Check for next page
            url = data['links'].get('next')

        print(f"✓ Found {len(all_records)} records")
        return all_records

    def get_record_text(self, record):
        """Extract text from a record.

        For now, we'll use the description/summary as text.
        In production, you'd download and extract the full text file.

        Args:
            record: InvenioRDM record dict

        Returns:
            Text content or None
        """
        metadata = record.get('metadata', {})

        # Combine multiple text fields
        text_parts = []

        # Title
        if 'title' in metadata:
            text_parts.append(metadata['title'])

        # Description
        if 'description' in metadata:
            text_parts.append(metadata['description'])

        # Subjects
        if 'subjects' in metadata:
            subjects = [s.get('subject', '') for s in metadata['subjects']]
            text_parts.append(' '.join(subjects))

        # Additional descriptions
        if 'additional_descriptions' in metadata:
            for desc in metadata['additional_descriptions']:
                if 'description' in desc:
                    text_parts.append(desc['description'])

        # For a full implementation, download the actual book file:
        # files = record.get('files', {}).get('entries', {})
        # for filename, file_info in files.items():
        #     if filename.endswith('.txt'):
        #         file_url = f"{self.api_url}/records/{record['id']}/files/{filename}/content"
        #         # Download and extract text...

        return ' '.join(text_parts) if text_parts else None

    def generate_embeddings(self, records):
        """Generate embeddings for all records.

        Args:
            records: List of InvenioRDM records

        Returns:
            Dictionary mapping record_id -> embedding
        """
        embeddings = {}

        print(f"\nGenerating embeddings for {len(records)} records...")
        print("This may take a few minutes...")
        print()

        for i, record in enumerate(records, 1):
            record_id = record['id']
            title = record.get('metadata', {}).get('title', 'Unknown')

            print(f"[{i}/{len(records)}] {title[:60]}... ", end='', flush=True)

            # Get text
            text = self.get_record_text(record)

            if not text or len(text.strip()) < 10:
                print("⚠ No text content, skipping")
                continue

            try:
                # Generate embedding
                embedding = self.model_manager.generate_embedding(text)

                # Convert numpy array to list for JSON serialization
                embeddings[record_id] = {
                    "embedding": embedding.tolist(),
                    "title": title,
                    "text_length": len(text),
                }

                print("✓")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        print(f"\n✓ Generated {len(embeddings)} embeddings")
        return embeddings

    def save_embeddings(self, embeddings):
        """Save embeddings to JSON file.

        Args:
            embeddings: Dictionary of embeddings
        """
        print(f"\nSaving embeddings to {self.output_file}...")

        with open(self.output_file, 'w') as f:
            json.dump(embeddings, f, indent=2)

        # Get file size
        file_size = os.path.getsize(self.output_file) / (1024 * 1024)  # MB

        print(f"✓ Saved {len(embeddings)} embeddings ({file_size:.1f} MB)")

    def run(self):
        """Run the full embedding generation process."""
        print("=" * 60)
        print("Embedding Generation for InvenioRDM Books")
        print("=" * 60)
        print()

        # Fetch records
        records = self.fetch_all_records()

        if not records:
            print("No records found!")
            return

        # Generate embeddings
        embeddings = self.generate_embeddings(records)

        if not embeddings:
            print("No embeddings generated!")
            return

        # Save to file
        self.save_embeddings(embeddings)

        print()
        print("=" * 60)
        print("✓ Embedding generation complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print(f"  1. Embeddings saved to: {self.output_file}")
        print("  2. These can be indexed into OpenSearch")
        print("  3. Use for semantic search queries")
        print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate embeddings for InvenioRDM records'
    )
    parser.add_argument(
        '-u', '--url',
        type=str,
        default='https://127.0.0.1:5000',
        help='InvenioRDM base URL (default: https://127.0.0.1:5000)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='embeddings.json',
        help='Output file (default: embeddings.json)'
    )

    args = parser.parse_args()

    generator = EmbeddingGenerator(
        base_url=args.url,
        output_file=args.output,
    )

    generator.run()


if __name__ == '__main__':
    main()
