# utils/session_manager.py
"""
Session and Context Manager for Planogram Analyzer
Manages user sessions, saved contexts, and analysis history
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import pickle
from pathlib import Path

class SessionManager:
    """
    Manages user sessions and analysis history
    """
    
    def __init__(self, session_dir: str = "cache/sessions"):
        """
        Initialize session manager
        
        Args:
            session_dir: Directory to store session data
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_timeout = timedelta(hours=24)  # Default 24 hour timeout
    
    def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Session ID
        """
        session_id = self._generate_session_id(user_id)
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'contexts': [],
            'analysis_history': [],
            'preferences': {}
        }
        
        session_file = self.session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found/expired
        """
        session_file = self.session_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Check if session has expired
        last_accessed = datetime.fromisoformat(session_data['last_accessed'])
        if datetime.now() - last_accessed > self.session_timeout:
            self.delete_session(session_id)
            return None
        
        # Update last accessed time
        session_data['last_accessed'] = datetime.now().isoformat()
        self.save_session(session_id, session_data)
        
        return session_data
    
    def save_session(self, session_id: str, session_data: Dict):
        """
        Save session data
        
        Args:
            session_id: Session identifier
            session_data: Session data to save
        """
        session_file = self.session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def delete_session(self, session_id: str):
        """
        Delete a session
        
        Args:
            session_id: Session identifier
        """
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
    
    def cleanup_expired_sessions(self):
        """
        Remove all expired sessions
        """
        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                last_accessed = datetime.fromisoformat(session_data['last_accessed'])
                if datetime.now() - last_accessed > self.session_timeout:
                    session_file.unlink()
            except Exception:
                # Remove corrupted session files
                session_file.unlink()
    
    def _generate_session_id(self, user_id: str) -> str:
        """
        Generate a unique session ID
        
        Args:
            user_id: User identifier
            
        Returns:
            Session ID
        """
        timestamp = datetime.now().isoformat()
        data = f"{user_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]


class ContextManager:
    """
    Manages saved prompts and contexts for analysis
    """
    
    def __init__(self, context_dir: str = "cache/contexts"):
        """
        Initialize context manager
        
        Args:
            context_dir: Directory to store context data
        """
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)
    
    def save_context(self, session_id: str, context: str, 
                    name: Optional[str] = None) -> str:
        """
        Save a context/prompt for future use
        
        Args:
            session_id: Session identifier
            context: Context/prompt text
            name: Optional name for the context
            
        Returns:
            Context ID
        """
        context_id = self._generate_context_id(session_id, context)
        
        context_data = {
            'id': context_id,
            'session_id': session_id,
            'name': name or f"Context_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'context': context,
            'created_at': datetime.now().isoformat(),
            'used_count': 0,
            'last_used': None,
            'tags': []
        }
        
        context_file = self.context_dir / f"{context_id}.json"
        with open(context_file, 'w') as f:
            json.dump(context_data, f, indent=2)
        
        return context_id
    
    def get_context(self, context_id: str) -> Optional[Dict]:
        """
        Retrieve a saved context
        
        Args:
            context_id: Context identifier
            
        Returns:
            Context data or None if not found
        """
        context_file = self.context_dir / f"{context_id}.json"
        
        if not context_file.exists():
            return None
        
        with open(context_file, 'r') as f:
            context_data = json.load(f)
        
        # Update usage statistics
        context_data['used_count'] += 1
        context_data['last_used'] = datetime.now().isoformat()
        
        with open(context_file, 'w') as f:
            json.dump(context_data, f, indent=2)
        
        return context_data
    
    def list_contexts(self, session_id: Optional[str] = None) -> List[Dict]:
        """
        List all saved contexts, optionally filtered by session
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            List of context summaries
        """
        contexts = []
        
        for context_file in self.context_dir.glob("*.json"):
            try:
                with open(context_file, 'r') as f:
                    context_data = json.load(f)
                
                if session_id and context_data.get('session_id') != session_id:
                    continue
                
                contexts.append({
                    'id': context_data['id'],
                    'name': context_data['name'],
                    'created_at': context_data['created_at'],
                    'used_count': context_data['used_count'],
                    'last_used': context_data.get('last_used')
                })
            except Exception:
                continue
        
        # Sort by last used or created date
        contexts.sort(key=lambda x: x.get('last_used') or x['created_at'], 
                     reverse=True)
        
        return contexts
    
    def delete_context(self, context_id: str):
        """
        Delete a saved context
        
        Args:
            context_id: Context identifier
        """
        context_file = self.context_dir / f"{context_id}.json"
        if context_file.exists():
            context_file.unlink()
    
    def merge_contexts(self, context_ids: List[str]) -> str:
        """
        Merge multiple contexts into one
        
        Args:
            context_ids: List of context IDs to merge
            
        Returns:
            Merged context text
        """
        merged_context = []
        
        for context_id in context_ids:
            context_data = self.get_context(context_id)
            if context_data:
                merged_context.append(context_data['context'])
        
        return "\n\n".join(merged_context)
    
    def _generate_context_id(self, session_id: str, context: str) -> str:
        """
        Generate a unique context ID
        
        Args:
            session_id: Session identifier
            context: Context text
            
        Returns:
            Context ID
        """
        data = f"{session_id}:{context[:100]}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class AnalysisHistory:
    """
    Manages analysis history and results
    """
    
    def __init__(self, history_dir: str = "cache/history"):
        """
        Initialize analysis history manager
        
        Args:
            history_dir: Directory to store history data
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def save_analysis(self, session_id: str, analysis_data: Dict) -> str:
        """
        Save an analysis result
        
        Args:
            session_id: Session identifier
            analysis_data: Analysis result data
            
        Returns:
            Analysis ID
        """
        analysis_id = self._generate_analysis_id(session_id)
        
        history_entry = {
            'id': analysis_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'analysis_mode': analysis_data.get('mode', 'bedrock'),
            'model_used': analysis_data.get('model'),
            'metrics': analysis_data.get('metrics', {}),
            'result': analysis_data.get('result', {}),
            'context_used': analysis_data.get('context_id'),
            'files': {
                'planogram': analysis_data.get('planogram_file'),
                'realogram': analysis_data.get('realogram_file'),
                'json_structure': analysis_data.get('json_structure_file')
            }
        }
        
        history_file = self.history_dir / f"{analysis_id}.json"
        with open(history_file, 'w') as f:
            json.dump(history_entry, f, indent=2)
        
        return analysis_id
    
    def get_analysis(self, analysis_id: str) -> Optional[Dict]:
        """
        Retrieve an analysis result
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Analysis data or None if not found
        """
        history_file = self.history_dir / f"{analysis_id}.json"
        
        if not history_file.exists():
            return None
        
        with open(history_file, 'r') as f:
            return json.load(f)
    
    def list_history(self, session_id: Optional[str] = None, 
                     limit: int = 10) -> List[Dict]:
        """
        List analysis history
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of entries to return
            
        Returns:
            List of analysis summaries
        """
        history = []
        
        for history_file in self.history_dir.glob("*.json"):
            try:
                with open(history_file, 'r') as f:
                    entry = json.load(f)
                
                if session_id and entry.get('session_id') != session_id:
                    continue
                
                history.append({
                    'id': entry['id'],
                    'timestamp': entry['timestamp'],
                    'mode': entry['analysis_mode'],
                    'model': entry.get('model_used'),
                    'compliance': entry.get('metrics', {}).get('overall_compliance', 0)
                })
            except Exception:
                continue
        
        # Sort by timestamp (most recent first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return history[:limit]
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict:
        """
        Get statistics from analysis history
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Statistics dictionary
        """
        history = self.list_history(session_id, limit=1000)
        
        if not history:
            return {
                'total_analyses': 0,
                'average_compliance': 0,
                'best_compliance': 0,
                'worst_compliance': 0,
                'most_used_mode': None,
                'most_used_model': None
            }
        
        compliances = [h['compliance'] for h in history if h.get('compliance')]
        modes = [h['mode'] for h in history if h.get('mode')]
        models = [h['model'] for h in history if h.get('model')]
        
        from collections import Counter
        mode_counter = Counter(modes)
        model_counter = Counter(models)
        
        return {
            'total_analyses': len(history),
            'average_compliance': sum(compliances) / len(compliances) if compliances else 0,
            'best_compliance': max(compliances) if compliances else 0,
            'worst_compliance': min(compliances) if compliances else 0,
            'most_used_mode': mode_counter.most_common(1)[0][0] if mode_counter else None,
            'most_used_model': model_counter.most_common(1)[0][0] if model_counter else None
        }
    
    def _generate_analysis_id(self, session_id: str) -> str:
        """
        Generate a unique analysis ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Analysis ID
        """
        timestamp = datetime.now().isoformat()
        data = f"{session_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:20]


# Utility functions for Streamlit integration
def get_or_create_session(user_id: str) -> tuple[str, Dict]:
    """
    Get existing session or create new one
    
    Args:
        user_id: User identifier
        
    Returns:
        Tuple of (session_id, session_data)
    """
    manager = SessionManager()
    
    # Try to find existing session for user
    for session_file in Path("cache/sessions").glob("*.json"):
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            if session_data.get('user_id') == user_id:
                session_id = session_file.stem
                session = manager.get_session(session_id)
                if session:
                    return session_id, session
        except Exception:
            continue
    
    # Create new session
    session_id = manager.create_session(user_id)
    session_data = manager.get_session(session_id)
    
    return session_id, session_data


def save_user_context(session_id: str, context: str, name: Optional[str] = None) -> str:
    """
    Save a user's context/prompt
    
    Args:
        session_id: Session identifier
        context: Context text
        name: Optional name for the context
        
    Returns:
        Context ID
    """
    manager = ContextManager()
    return manager.save_context(session_id, context, name)


def get_user_contexts(session_id: str) -> List[Dict]:
    """
    Get all contexts for a user session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of context summaries
    """
    manager = ContextManager()
    return manager.list_contexts(session_id)


def save_analysis_result(session_id: str, analysis_data: Dict) -> str:
    """
    Save an analysis result to history
    
    Args:
        session_id: Session identifier
        analysis_data: Analysis data
        
    Returns:
        Analysis ID
    """
    manager = AnalysisHistory()
    return manager.save_analysis(session_id, analysis_data)


def get_analysis_history(session_id: str, limit: int = 10) -> List[Dict]:
    """
    Get analysis history for a session
    
    Args:
        session_id: Session identifier
        limit: Maximum number of entries
        
    Returns:
        List of analysis summaries
    """
    manager = AnalysisHistory()
    return manager.list_history(session_id, limit)


def get_analysis_statistics(session_id: Optional[str] = None) -> Dict:
    """
    Get analysis statistics
    
    Args:
        session_id: Optional session identifier
        
    Returns:
        Statistics dictionary
    """
    manager = AnalysisHistory()
    return manager.get_statistics(session_id)