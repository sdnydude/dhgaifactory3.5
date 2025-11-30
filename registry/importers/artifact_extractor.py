"""
Extract artifacts from Claude conversation content
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ArtifactExtractor:
    """Extract artifacts from conversation messages"""
    
    # Patterns for detecting code blocks and artifacts
    CODE_BLOCK_PATTERN = r'```(\w+)?\n(.*?)```'
    ARTIFACT_MARKERS = [
        'artifact',
        'code snippet',
        'generated code',
        'here\'s the code',
        'here is the code'
    ]
    
    def __init__(self):
        self.artifact_types = {
            'python': 'code',
            'javascript': 'code',
            'typescript': 'code',
            'java': 'code',
            'cpp': 'code',
            'c': 'code',
            'go': 'code',
            'rust': 'code',
            'ruby': 'code',
            'php': 'code',
            'html': 'html',
            'css': 'html',
            'svg': 'svg',
            'jsx': 'react_component',
            'tsx': 'react_component',
            'markdown': 'document',
            'md': 'document',
            'json': 'document',
            'yaml': 'document',
            'xml': 'document'
        }
    
    def extract_from_conversation(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all artifacts from a conversation
        
        Args:
            conversation: Conversation dict with 'messages' list
        
        Returns:
            List of artifact dicts
        """
        artifacts = []
        
        messages = conversation.get('messages', [])
        for message in messages:
            if message.get('role') != 'assistant':
                continue
            
            msg_artifacts = self.extract_from_message(message)
            artifacts.extend(msg_artifacts)
        
        logger.info(f"Extracted {len(artifacts)} artifacts from conversation")
        return artifacts
    
    def extract_from_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract artifacts from a single message"""
        artifacts = []
        content = message.get('content', '')
        
        if not content:
            return artifacts
        
        # Extract code blocks
        code_blocks = re.finditer(self.CODE_BLOCK_PATTERN, content, re.DOTALL)
        
        artifact_index = 0
        for match in code_blocks:
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            
            if not code:
                continue
            
            # Determine artifact type
            artifact_type = self.artifact_types.get(language.lower(), 'code')
            
            # Generate title
            title = self._generate_title(code, language, artifact_index)
            
            artifact = {
                'message_id': message.get('id'),
                'title': title,
                'artifact_type': artifact_type,
                'language': language,
                'content': code,
                'file_path': None,
                'published_url': None,
                'meta_data': {
                    'message_index': message.get('message_index'),
                    'extracted': True,
                    'code_block_index': artifact_index
                }
            }
            
            artifacts.append(artifact)
            artifact_index += 1
        
        # Also check for artifact mentions without code blocks
        if self._has_artifact_mention(content) and not artifacts:
            # Treat entire message as artifact if it appears to be one
            artifact = {
                'message_id': message.get('id'),
                'title': 'Document Artifact',
                'artifact_type': 'document',
                'language': None,
                'content': content,
                'file_path': None,
                'published_url': None,
                'meta_data': {
                    'message_index': message.get('message_index'),
                    'extracted': True,
                    'full_message': True
                }
            }
            artifacts.append(artifact)
        
        return artifacts
    
    def _generate_title(self, code: str, language: str, index: int) -> str:
        """Generate a title for the artifact"""
        # Try to extract meaningful title from code
        lines = code.split('\n')
        
        # Look for function/class names
        for line in lines[:10]:
            # Python/JS function
            match = re.match(r'(?:def|function|class)\s+(\w+)', line)
            if match:
                return f"{match.group(1)} ({language})"
            
            # Component name
            match = re.match(r'(?:export\s+)?(?:const|let|var)\s+(\w+)', line)
            if match:
                return f"{match.group(1)} ({language})"
        
        # Default title
        return f"{language.capitalize()} Code {index + 1}"
    
    def _has_artifact_mention(self, content: str) -> bool:
        """Check if content mentions artifacts"""
        content_lower = content.lower()
        return any(marker in content_lower for marker in self.ARTIFACT_MARKERS)
    
    def save_artifacts_to_disk(self, artifacts: List[Dict[str, Any]], output_dir: str) -> None:
        """
        Save artifacts to disk
        
        Args:
            artifacts: List of artifact dicts
            output_dir: Directory to save files
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for idx, artifact in enumerate(artifacts):
            language = artifact.get('language', 'txt')
            title = artifact.get('title', f'artifact_{idx}')
            
            # Clean title for filename
            filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            filename = f"{idx:03d}_{filename}.{language}"
            
            file_path = output_path / filename
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(artifact['content'])
                
                artifact['file_path'] = str(file_path)
                logger.info(f"Saved artifact to {file_path}")
            except Exception as e:
                logger.error(f"Failed to save artifact {filename}: {e}")
