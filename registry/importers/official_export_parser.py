"""
Parser for Claude AI official export format (ZIP with JSON/DMS files)
"""
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OfficialExportParser:
    """Parse Claude's official data export ZIP file"""
    
    def __init__(self, zip_path: str):
        self.zip_path = Path(zip_path)
        if not self.zip_path.exists():
            raise FileNotFoundError(f"Export file not found: {zip_path}")
        if not zipfile.is_zipfile(self.zip_path):
            raise ValueError(f"Not a valid ZIP file: {zip_path}")
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse the entire export and return structured data
        
        Returns:
            {
                'conversations': [...],
                'projects': [...],
                'user_data': {...}
            }
        """
        result = {
            'conversations': [],
            'projects': [],
            'user_data': {}
        }
        
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            # List all files in the archive
            file_list = zf.namelist()
            logger.info(f"Found {len(file_list)} files in export")
            
            # Look for conversations data
            for filename in file_list:
                try:
                    if 'conversation' in filename.lower() and filename.endswith('.json'):
                        data = json.loads(zf.read(filename).decode('utf-8'))
                        result['conversations'].extend(self._parse_conversations(data))
                    
                    elif 'project' in filename.lower() and filename.endswith('.json'):
                        data = json.loads(zf.read(filename).decode('utf-8'))
                        result['projects'].extend(self._parse_projects(data))
                    
                    elif 'user' in filename.lower() and filename.endswith('.json'):
                        data = json.loads(zf.read(filename).decode('utf-8'))
                        result['user_data'] = data
                
                except Exception as e:
                    logger.warning(f"Failed to parse {filename}: {e}")
                    continue
        
        logger.info(f"Parsed {len(result['conversations'])} conversations, {len(result['projects'])} projects")
        return result
    
    def _parse_conversations(self, data: Any) -> List[Dict[str, Any]]:
        """Parse conversation data from various export formats"""
        conversations = []
        
        # Handle different data structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys
            items = data.get('conversations', data.get('chats', data.get('data', [])))
            if not isinstance(items, list):
                items = [data]
        else:
            logger.warning(f"Unexpected conversation data type: {type(data)}")
            return conversations
        
        for item in items:
            try:
                conv = self._parse_single_conversation(item)
                if conv:
                    conversations.append(conv)
            except Exception as e:
                logger.warning(f"Failed to parse conversation: {e}")
                continue
        
        return conversations
    
    def _parse_single_conversation(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single conversation"""
        if not isinstance(data, dict):
            return None
        
        # Extract conversation metadata
        conversation = {
            'conversation_id': data.get('uuid', data.get('id', data.get('conversation_id'))),
            'title': data.get('name', data.get('title', 'Untitled Conversation')),
            'model_name': data.get('model', data.get('model_name')),
            'created_at': self._parse_timestamp(data.get('created_at', data.get('created'))),
            'updated_at': self._parse_timestamp(data.get('updated_at', data.get('updated'))),
            'project_id': data.get('project_uuid', data.get('project_id')),
            'export_source': 'official_export',
            'messages': [],
            'meta_data': {
                'raw_data': data
            }
        }
        
        # Parse messages
        messages = data.get('chat_messages', data.get('messages', []))
        for idx, msg in enumerate(messages):
            try:
                parsed_msg = self._parse_message(msg, idx)
                if parsed_msg:
                    conversation['messages'].append(parsed_msg)
            except Exception as e:
                logger.warning(f"Failed to parse message {idx}: {e}")
                continue
        
        return conversation
    
    def _parse_message(self, data: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Parse a single message"""
        if not isinstance(data, dict):
            return None
        
        # Extract message content
        content = data.get('text', data.get('content', ''))
        
        # Handle different content structures
        if isinstance(content, list):
            # Content may be an array of content blocks
            content = '\n'.join(
                block.get('text', str(block)) if isinstance(block, dict) else str(block)
                for block in content
            )
        elif not isinstance(content, str):
            content = str(content)
        
        message = {
            'message_index': index,
            'role': data.get('sender', data.get('role', 'user')),
            'content': content,
            'created_at': self._parse_timestamp(data.get('created_at', data.get('timestamp'))),
            'attachments': data.get('attachments', []),
            'meta_data': {
                'raw_data': data
            }
        }
        
        return message
    
    def _parse_projects(self, data: Any) -> List[Dict[str, Any]]:
        """Parse project data"""
        projects = []
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('projects', [data])
        else:
            return projects
        
        for item in items:
            try:
                project = {
                    'project_id': item.get('uuid', item.get('id')),
                    'name': item.get('name', 'Untitled Project'),
                    'description': item.get('description', ''),
                    'custom_instructions': item.get('custom_instructions', item.get('instructions', '')),
                    'knowledge_files': item.get('documents', item.get('files', [])),
                    'created_at': self._parse_timestamp(item.get('created_at')),
                    'updated_at': self._parse_timestamp(item.get('updated_at')),
                    'meta_data': {
                        'raw_data': item
                    }
                }
                projects.append(project)
            except Exception as e:
                logger.warning(f"Failed to parse project: {e}")
                continue
        
        return projects
    
    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse various timestamp formats"""
        if not ts:
            return None
        
        if isinstance(ts, datetime):
            return ts
        
        if isinstance(ts, (int, float)):
            # Unix timestamp
            try:
                return datetime.fromtimestamp(ts)
            except:
                return None
        
        if isinstance(ts, str):
            # ISO format
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        
        return None
