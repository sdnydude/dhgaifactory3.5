#!/usr/bin/env python3
"""
Claude Data Ingestion CLI Tool
Imports Claude conversations, projects, and artifacts into the DHG Registry
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import models and parsers
from models import Base, Project, Conversation, Message, Artifact, Event
from importers.official_export_parser import OfficialExportParser
from importers.markdown_parser import MarkdownParser, MarkdownBatchParser
from importers.artifact_extractor import ArtifactExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaudeDataIngester:
    """Ingest Claude data into the registry database"""
    
    def __init__(self, database_url: str, dry_run: bool = False):
        self.dry_run = dry_run
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.artifact_extractor = ArtifactExtractor()
        
        self.stats = {
            'projects_created': 0,
            'conversations_created': 0,
            'conversations_updated': 0,
            'messages_created': 0,
            'artifacts_created': 0,
            'errors': 0
        }
    
    def ingest_official_export(self, zip_path: str, merge: bool = False) -> Dict[str, int]:
        """Ingest Claude official export ZIP file"""
        logger.info(f"Parsing official export: {zip_path}")
        
        try:
            parser = OfficialExportParser(zip_path)
            data = parser.parse()
        except Exception as e:
            logger.error(f"Failed to parse export: {e}")
            return self.stats
        
        # Ingest projects first
        for project_data in data.get('projects', []):
            self._ingest_project(project_data)
        
        # Then ingest conversations
        for conv_data in data.get('conversations', []):
            self._ingest_conversation(conv_data, merge=merge)
        
        return self.stats
    
    def ingest_markdown_file(self, file_path: str, merge: bool = False) -> Dict[str, int]:
        """Ingest single markdown file"""
        logger.info(f"Parsing markdown file: {file_path}")
        
        try:
            parser = MarkdownParser(file_path)
            conv_data = parser.parse()
            self._ingest_conversation(conv_data, merge=merge)
        except Exception as e:
            logger.error(f"Failed to parse markdown: {e}")
            self.stats['errors'] += 1
        
        return self.stats
    
    def ingest_markdown_directory(self, dir_path: str, merge: bool = False) -> Dict[str, int]:
        """Ingest all markdown files from directory"""
        logger.info(f"Parsing markdown directory: {dir_path}")
        
        try:
            parser = MarkdownBatchParser(dir_path)
            conversations = parser.parse_all()
            
            for conv_data in conversations:
                self._ingest_conversation(conv_data, merge=merge)
        except Exception as e:
            logger.error(f"Failed to parse markdown directory: {e}")
            self.stats['errors'] += 1
        
        return self.stats
    
    def _ingest_project(self, project_data: Dict[str, Any]) -> None:
        """Ingest a single project"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create project: {project_data.get('name')}")
            return
        
        session = self.Session()
        try:
            # Check if project already exists
            project_id = project_data.get('project_id')
            existing = None
            if project_id:
                existing = session.query(Project).filter_by(project_id=project_id).first()
            
            if existing:
                logger.info(f"Project already exists: {project_data.get('name')}")
                session.close()
                return
            
            # Create new project
            project = Project(
                name=project_data['name'],
                project_id=project_data.get('project_id'),
                description=project_data.get('description'),
                custom_instructions=project_data.get('custom_instructions'),
                knowledge_files=project_data.get('knowledge_files'),
                created_at=project_data.get('created_at') or datetime.now(),
                updated_at=project_data.get('updated_at') or datetime.now(),
                meta_data=project_data.get('meta_data', {})
            )
            
            session.add(project)
            session.commit()
            
            # Log event
            event = Event(
                event_type='create',
                entity_type='project',
                entity_id=project.id,
                description=f"Imported project: {project.name}",
                meta_data={'source': 'claude_import'}
            )
            session.add(event)
            session.commit()
            
            self.stats['projects_created'] += 1
            logger.info(f"Created project: {project.name}")
        
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create project: {e}")
            self.stats['errors'] += 1
        finally:
            session.close()
    
    def _ingest_conversation(self, conv_data: Dict[str, Any], merge: bool = False) -> None:
        """Ingest a single conversation with messages and artifacts"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create conversation: {conv_data.get('title')}")
            return
        
        session = self.Session()
        try:
            # Check for existing conversation
            conversation_id = conv_data.get('conversation_id')
            existing = None
            if conversation_id:
                existing = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
            
            if existing:
                if merge:
                    logger.info(f"Updating existing conversation: {conv_data.get('title')}")
                    conversation = existing
                    conversation.title = conv_data['title']
                    conversation.model_name = conv_data.get('model_name') or conversation.model_name
                    conversation.updated_at = datetime.now()
                    conversation.meta_data = conv_data.get('meta_data', {})
                    self.stats['conversations_updated'] += 1
                else:
                    logger.info(f"Conversation already exists (skipping): {conv_data.get('title')}")
                    session.close()
                    return
            else:
                # Find project if referenced
                project = None
                project_id_ref = conv_data.get('project_id')
                if project_id_ref:
                    project = session.query(Project).filter_by(project_id=project_id_ref).first()
                
                # Create new conversation
                conversation = Conversation(
                    title=conv_data['title'],
                    conversation_id=conversation_id,
                    export_source=conv_data.get('export_source', 'manual'),
                    model_name=conv_data.get('model_name'),
                    project_id=project.id if project else None,
                    created_at=conv_data.get('created_at') or datetime.now(),
                    updated_at=conv_data.get('updated_at') or datetime.now(),
                    meta_data=conv_data.get('meta_data', {})
                )
                session.add(conversation)
                session.flush()  # Get conversation ID
                self.stats['conversations_created'] += 1
            
            # Ingest messages
            messages_data = conv_data.get('messages', [])
            message_objects = []
            
            for msg_data in messages_data:
                message = Message(
                    conversation_id=conversation.id,
                    message_index=msg_data['message_index'],
                    role=msg_data['role'],
                    content=msg_data['content'],
                    attachments=msg_data.get('attachments'),
                    created_at=msg_data.get('created_at') or datetime.now(),
                    meta_data=msg_data.get('meta_data', {})
                )
                session.add(message)
                message_objects.append(message)
                self.stats['messages_created'] += 1
            
            session.flush()  # Get message IDs
            
            # Extract and ingest artifacts
            artifacts = self.artifact_extractor.extract_from_conversation(conv_data)
            
            for artifact_data in artifacts:
                artifact = Artifact(
                    conversation_id=conversation.id,
                    message_id=None,  # Will link after we have message IDs
                    title=artifact_data['title'],
                    artifact_type=artifact_data['artifact_type'],
                    language=artifact_data.get('language'),
                    content=artifact_data['content'],
                    file_path=artifact_data.get('file_path'),
                    published_url=artifact_data.get('published_url'),
                    meta_data=artifact_data.get('meta_data', {})
                )
                session.add(artifact)
                self.stats['artifacts_created'] += 1
            
            # Log event
            event = Event(
                event_type='create' if not existing else 'update',
                entity_type='conversation',
                entity_id=conversation.id,
                description=f"Imported conversation: {conversation.title}",
                meta_data={
                    'source': conv_data.get('export_source', 'manual'),
                    'message_count': len(messages_data),
                    'artifact_count': len(artifacts)
                }
            )
            session.add(event)
            
            session.commit()
            logger.info(f"Imported conversation: {conversation.title} ({len(messages_data)} messages, {len(artifacts)} artifacts)")
        
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Duplicate conversation (skipping): {conv_data.get('title')}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to import conversation: {e}")
            self.stats['errors'] += 1
        finally:
            session.close()
    
    def print_stats(self) -> None:
        """Print ingestion statistics"""
        print("\n" + "="*50)
        print("INGESTION COMPLETE")
        print("="*50)
        print(f"Projects created:        {self.stats['projects_created']}")
        print(f"Conversations created:   {self.stats['conversations_created']}")
        print(f"Conversations updated:   {self.stats['conversations_updated']}")
        print(f"Messages created:        {self.stats['messages_created']}")
        print(f"Artifacts created:       {self.stats['artifacts_created']}")
        print(f"Errors:                  {self.stats['errors']}")
        print("="*50)


def get_database_url() -> str:
    """Get database URL from environment"""
    import os
    
    db_password_file = os.getenv("DB_PASSWORD_FILE", "./secrets/db_password.txt")
    try:
        with open(db_password_file, 'r') as f:
            password = f.read().strip()
    except FileNotFoundError:
        password = os.getenv("DB_PASSWORD", "dhg_password")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://dhg_user@localhost:5432/dhg_registry")
    
    # Insert password
    if "@" in db_url:
        protocol, rest = db_url.split("://", 1)
        user_host = rest.split("@", 1)
        if len(user_host) == 2:
            user, host = user_host
            db_url = f"{protocol}://{user}:{password}@{host}"
    
    return db_url


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Claude AI data into DHG Registry"
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input file or directory (ZIP for official export, .md file, or directory of .md files)'
    )
    parser.add_argument(
        '--source', '-s',
        choices=['official_export', 'markdown', 'markdown_dir'],
        required=True,
        help='Type of input source'
    )
    parser.add_argument(
        '--merge', '-m',
        action='store_true',
        help='Merge/update existing conversations instead of skipping'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Validate input without writing to database'
    )
    parser.add_argument(
        '--database-url',
        help='Database URL (defaults to environment settings)'
    )
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.database_url or get_database_url()
    
    # Create ingester
    ingester = ClaudeDataIngester(db_url, dry_run=args.dry_run)
    
    # Ingest based on source type
    try:
        if args.source == 'official_export':
            ingester.ingest_official_export(args.input, merge=args.merge)
        elif args.source == 'markdown':
            ingester.ingest_markdown_file(args.input, merge=args.merge)
        elif args.source == 'markdown_dir':
            ingester.ingest_markdown_directory(args.input, merge=args.merge)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
    
    # Print statistics
    ingester.print_stats()
    
    # Exit with error code if there were errors
    if ingester.stats['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
