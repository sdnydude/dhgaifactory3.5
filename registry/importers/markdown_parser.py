"""
Parser for Markdown exports from browser extensions (Claude Exporter, etc.)
"""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parse Markdown formatted Claude conversation exports"""
    
    # Common patterns for detecting user/assistant messages
    USER_PATTERNS = [
        r'^##?\s*(?:User|Human|Me|You)[\s:]*$',
        r'^\*\*(?:User|Human|Me|You)\*\*[\s:]*$',
        r'^_(?:User|Human|Me|You)_[\s:]*$',
        r'^(?:User|Human|Me|You)[\s:]*$',
    ]
    
    ASSISTANT_PATTERNS = [
        r'^##?\s*(?:Claude|Assistant|AI)[\s:]*$',
        r'^\*\*(?:Claude|Assistant|AI)\*\*[\s:]*$',
        r'^_(?:Claude|Assistant|AI)_[\s:]*$',
        r'^(?:Claude|Assistant|AI)[\s:]*$',
    ]
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse markdown file and return conversation data
        
        Returns:
            {
                'title': str,
                'messages': [...],
                'export_date': datetime,
                'meta_data': {...}
            }
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title (first # heading or filename)
        title = self._extract_title(content)
        
        # Extract export metadata if present
        export_date = self._extract_export_date(content)
        
        # Parse messages
        messages = self._parse_messages(content)
        
        return {
            'title': title,
            'conversation_id': None,  # Browser extensions usually don't have this
            'model_name': None,  # Usually not in markdown exports
            'created_at': export_date or datetime.now(),
            'updated_at': export_date or datetime.now(),
            'export_source': 'browser_extension',
            'messages': messages,
            'meta_data': {
                'source_file': str(self.file_path),
                'export_date': export_date.isoformat() if export_date else None
            }
        }
    
    def _extract_title(self, content: str) -> str:
        """Extract conversation title from content"""
        # Try to find first # heading
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fall back to filename
        return self.file_path.stem
    
    def _extract_export_date(self, content: str) -> Optional[datetime]:
        """Try to extract export date from metadata"""
        # Look for date patterns in first few lines
        lines = content.split('\n')
        for line in lines[:20]:
            # Pattern: "Exported: 2024-11-30" or similar
            match = re.search(r'(?:exported|created|date)[\s:]*(\d{4}-\d{2}-\d{2})', line, re.IGNORECASE)
            if match:
                try:
                    return datetime.fromisoformat(match.group(1))
                except:
                    pass
        return None
    
    def _parse_messages(self, content: str) -> List[Dict[str, Any]]:
        """Parse messages from markdown content"""
        messages = []
        current_role = None
        current_content = []
        message_index = 0
        
        lines = content.split('\n')
        
        for line in lines:
            # Check if this line indicates a role change
            is_user = self._is_user_marker(line)
            is_assistant = self._is_assistant_marker(line)
            
            if is_user or is_assistant:
                # Save previous message if exists
                if current_role and current_content:
                    messages.append({
                        'message_index': message_index,
                        'role': current_role,
                        'content': '\n'.join(current_content).strip(),
                        'created_at': None,
                        'attachments': [],
                        'meta_data': {}
                    })
                    message_index += 1
                    current_content = []
                
                # Set new role
                current_role = 'user' if is_user else 'assistant'
            else:
                # Add to current message content
                if current_role:
                    current_content.append(line)
        
        # Save last message
        if current_role and current_content:
            messages.append({
                'message_index': message_index,
                'role': current_role,
                'content': '\n'.join(current_content).strip(),
                'created_at': None,
                'attachments': [],
                'meta_data': {}
            })
        
        # If no role markers found, try to parse as alternating user/assistant
        if not messages:
            messages = self._parse_alternating_format(content)
        
        return messages
    
    def _is_user_marker(self, line: str) -> bool:
        """Check if line indicates user message"""
        line = line.strip()
        for pattern in self.USER_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _is_assistant_marker(self, line: str) -> bool:
        """Check if line indicates assistant message"""
        line = line.strip()
        for pattern in self.ASSISTANT_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _parse_alternating_format(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse format where messages alternate without explicit markers
        Split on horizontal rules (---) or blank lines
        """
        messages = []
        
        # Try splitting on horizontal rules first
        sections = re.split(r'\n---+\n', content)
        
        if len(sections) < 2:
            # Try splitting on double blank lines
            sections = re.split(r'\n\n+', content)
        
        # Assume alternating user/assistant
        for idx, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            
            messages.append({
                'message_index': idx,
                'role': 'user' if idx % 2 == 0 else 'assistant',
                'content': section,
                'created_at': None,
                'attachments': [],
                'meta_data': {}
            })
        
        return messages


class MarkdownBatchParser:
    """Parse multiple markdown files from a directory"""
    
    def __init__(self, directory: str):
        self.directory = Path(directory)
        if not self.directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
    
    def parse_all(self, pattern: str = "*.md") -> List[Dict[str, Any]]:
        """Parse all markdown files matching pattern"""
        conversations = []
        
        for file_path in self.directory.glob(pattern):
            if file_path.is_file():
                try:
                    parser = MarkdownParser(str(file_path))
                    conv = parser.parse()
                    conversations.append(conv)
                    logger.info(f"Parsed {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to parse {file_path.name}: {e}")
                    continue
        
        logger.info(f"Parsed {len(conversations)} conversations from {self.directory}")
        return conversations
