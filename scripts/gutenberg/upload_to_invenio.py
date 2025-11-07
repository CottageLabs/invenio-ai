#!/usr/bin/env python3
"""
Upload Project Gutenberg books to InvenioRDM.
Reads metadata and text files from the Gutenberg download and creates InvenioRDM records.
"""

import json
import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class InvenioUploader:
    """Upload books to InvenioRDM via REST API."""

    def __init__(
        self,
        base_url: str = "https://127.0.0.1:5000",
        token_file: str = "scripts/gutenberg/.api_token",
        data_dir: str = "gutenberg_data"
    ):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.data_dir = Path(data_dir)

        # Load API token
        token_path = Path(token_file)
        if not token_path.exists():
            raise FileNotFoundError(
                f"API token not found at {token_file}. "
                "Run scripts/gutenberg/setup_user.sh first."
            )

        self.token = token_path.read_text().strip()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_metadata(self, book_meta: Dict) -> Dict:
        """
        Convert Gutenberg metadata to InvenioRDM format.

        Args:
            book_meta: Gutenberg book metadata from Gutendex

        Returns:
            InvenioRDM-formatted metadata dictionary
        """
        # Extract authors
        creators = []
        for author in book_meta.get('authors', []):
            author_name = author.get('name', 'Unknown Author')
            # Parse "Last, First" format
            if ',' in author_name:
                parts = author_name.split(',', 1)
                family_name = parts[0].strip()
                given_name = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Use full name as family name if no comma
                family_name = author_name
                given_name = ""

            creator = {
                "person_or_org": {
                    "type": "personal",
                    "name": author_name,
                }
            }

            if given_name:
                creator["person_or_org"]["given_name"] = given_name
            if family_name:
                creator["person_or_org"]["family_name"] = family_name

            creators.append(creator)

        # If no authors, use "Unknown"
        if not creators:
            creators = [{
                "person_or_org": {
                    "type": "personal",
                    "name": "Unknown Author",
                    "family_name": "Unknown",
                }
            }]

        # Extract subjects
        subjects = []
        for subject in book_meta.get('subjects', []):
            subjects.append({"subject": subject})

        # Use first bookshelf as additional subject if available
        if book_meta.get('bookshelves'):
            for shelf in book_meta['bookshelves'][:3]:  # Limit to 3
                subjects.append({"subject": shelf})

        # Build description from summary if available
        description = ""
        if book_meta.get('summaries'):
            description = book_meta['summaries'][0]

        # Determine publication date (use current year as fallback)
        pub_date = "1900-01-01"  # Default for old public domain books

        # Create InvenioRDM metadata
        metadata = {
            "resource_type": {"id": "publication-book"},
            "title": book_meta.get('title', f"Book {book_meta.get('id')}"),
            "creators": creators,
            "publication_date": pub_date,
        }

        # Add optional fields
        if description:
            metadata["description"] = description

        if subjects:
            metadata["subjects"] = subjects

        # Add publisher
        metadata["publisher"] = "Project Gutenberg"

        # Add rights information
        metadata["rights"] = [{
            "title": {"en": "Public Domain"},
            "description": {
                "en": "This work is in the public domain in the United States."
            },
        }]

        # Add additional description with Project Gutenberg ID
        metadata["additional_descriptions"] = [{
            "description": f"Project Gutenberg eBook #{book_meta.get('id')}. "
                         f"Downloaded from https://www.gutenberg.org/ebooks/{book_meta.get('id')}",
            "type": {"id": "other"}
        }]

        return metadata

    def create_draft(self, metadata: Dict) -> Optional[Dict]:
        """
        Create a draft record in InvenioRDM.

        Args:
            metadata: InvenioRDM-formatted metadata

        Returns:
            Draft record response or None if failed
        """
        payload = {
            "access": {
                "record": "public",
                "files": "public"
            },
            "files": {
                "enabled": True
            },
            "metadata": metadata
        }

        try:
            response = requests.post(
                f"{self.api_url}/records",
                headers=self.headers,
                json=payload,
                verify=False  # Self-signed cert
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  Error creating draft: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None

    def upload_file(self, record_id: str, filename: str, file_path: Path) -> bool:
        """
        Upload a file to a draft record.

        Args:
            record_id: Draft record ID
            filename: Name for the file
            file_path: Path to the file to upload

        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Initiate file upload
            init_payload = [{"key": filename}]
            response = requests.post(
                f"{self.api_url}/records/{record_id}/draft/files",
                headers=self.headers,
                json=init_payload,
                verify=False
            )
            response.raise_for_status()

            # Step 2: Upload file content
            with open(file_path, 'rb') as f:
                content_headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/octet-stream",
                }
                response = requests.put(
                    f"{self.api_url}/records/{record_id}/draft/files/{filename}/content",
                    headers=content_headers,
                    data=f,
                    verify=False
                )
                response.raise_for_status()

            # Step 3: Commit the file
            response = requests.post(
                f"{self.api_url}/records/{record_id}/draft/files/{filename}/commit",
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"  Error uploading file: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return False

    def publish_draft(self, record_id: str) -> Optional[Dict]:
        """
        Publish a draft record.

        Args:
            record_id: Draft record ID

        Returns:
            Published record response or None if failed
        """
        try:
            response = requests.post(
                f"{self.api_url}/records/{record_id}/draft/actions/publish",
                headers=self.headers,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  Error publishing draft: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None

    def upload_book(self, book_metadata_file: Path) -> bool:
        """
        Upload a single book to InvenioRDM.

        Args:
            book_metadata_file: Path to the book's metadata JSON file

        Returns:
            True if successful, False otherwise
        """
        # Load metadata
        with open(book_metadata_file, 'r', encoding='utf-8') as f:
            gutenberg_meta = json.load(f)

        book_id = gutenberg_meta['id']
        title = gutenberg_meta.get('title', f'Book {book_id}')

        print(f"\nUploading: {title} (ID: {book_id})")

        # Find the corresponding text file
        base_name = book_metadata_file.stem  # Remove .json
        text_file = self.data_dir / "books" / f"{base_name}.txt"

        if not text_file.exists():
            print(f"  ✗ Text file not found: {text_file}")
            return False

        # Create metadata
        print(f"  Creating draft record...")
        invenio_metadata = self.create_metadata(gutenberg_meta)
        draft = self.create_draft(invenio_metadata)

        if not draft:
            print(f"  ✗ Failed to create draft")
            return False

        record_id = draft['id']
        print(f"  ✓ Draft created (ID: {record_id})")

        # Upload file
        print(f"  Uploading text file...")
        if not self.upload_file(record_id, f"{base_name}.txt", text_file):
            print(f"  ✗ Failed to upload file")
            return False

        print(f"  ✓ File uploaded")

        # Publish
        print(f"  Publishing record...")
        published = self.publish_draft(record_id)

        if not published:
            print(f"  ✗ Failed to publish")
            return False

        record_url = f"{self.base_url}/records/{published['id']}"
        print(f"  ✓ Published: {record_url}")

        return True

    def upload_all(self, limit: Optional[int] = None):
        """
        Upload all books from the metadata directory.

        Args:
            limit: Optional limit on number of books to upload
        """
        metadata_dir = self.data_dir / "metadata"

        if not metadata_dir.exists():
            print(f"Metadata directory not found: {metadata_dir}")
            return

        # Get all metadata files
        metadata_files = sorted(metadata_dir.glob("*.json"))

        if limit:
            metadata_files = metadata_files[:limit]

        print(f"{'='*60}")
        print(f"Uploading {len(metadata_files)} books to InvenioRDM")
        print(f"API: {self.api_url}")
        print(f"{'='*60}")

        successful = 0
        failed = []

        for i, metadata_file in enumerate(metadata_files, 1):
            print(f"\n[{i}/{len(metadata_files)}]", end=" ")

            if self.upload_book(metadata_file):
                successful += 1
            else:
                failed.append(metadata_file.stem)

            # Rate limiting - be nice to the server
            time.sleep(1)

        # Summary
        print(f"\n{'='*60}")
        print(f"Upload Summary:")
        print(f"  Successful: {successful}/{len(metadata_files)}")
        print(f"  Failed: {len(failed)}")

        if failed:
            print(f"\nFailed uploads:")
            for name in failed:
                print(f"  - {name}")

        print(f"{'='*60}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Upload Project Gutenberg books to InvenioRDM'
    )
    parser.add_argument(
        '-d', '--data-dir',
        type=str,
        default='gutenberg_data',
        help='Directory containing downloaded books (default: gutenberg_data)'
    )
    parser.add_argument(
        '-u', '--url',
        type=str,
        default='https://127.0.0.1:5000',
        help='InvenioRDM base URL (default: https://127.0.0.1:5000)'
    )
    parser.add_argument(
        '-t', '--token-file',
        type=str,
        default='scripts/gutenberg/.api_token',
        help='API token file (default: scripts/gutenberg/.api_token)'
    )
    parser.add_argument(
        '-n', '--limit',
        type=int,
        help='Limit number of books to upload (default: all)'
    )

    args = parser.parse_args()

    uploader = InvenioUploader(
        base_url=args.url,
        token_file=args.token_file,
        data_dir=args.data_dir
    )

    uploader.upload_all(limit=args.limit)


if __name__ == '__main__':
    main()
