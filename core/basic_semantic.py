#!/usr/bin/env python3
"""
🔍 Ultra-Basic Semantic Search for MySecondMind (Under 400MB)

This module provides basic intelligent search without ANY heavy dependencies:
- Pure Python text processing
- Smart keyword matching with synonyms
- No ML libraries required
- Still provides intelligent search capabilities
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class BasicSemanticEngine:
    """Ultra-basic semantic search using pure Python."""
    
    def __init__(self):
        self.content_index = {}  # content_id -> processed words
        self.content_metadata = {}  # content_id -> metadata
        
        # Comprehensive synonym mappings
        self.synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'deep learning', 'neural', 'algorithm', 'gpt', 'chatgpt', 'openai', 'llm'],
            'gpt': ['ai', 'artificial intelligence', 'chatgpt', 'openai', 'language model', 'llm'],
            'chatgpt': ['ai', 'gpt', 'openai', 'artificial intelligence', 'language model'],
            'productivity': ['efficiency', 'time management', 'organization', 'workflow', 'optimization', 'performance'],
            'programming': ['coding', 'development', 'software', 'code', 'dev', 'tech', 'computer'],
            'task': ['todo', 'work', 'assignment', 'job', 'project', 'activity'],
            'note': ['information', 'data', 'knowledge', 'content', 'memo', 'record'],
            'reminder': ['alert', 'notification', 'memory', 'prompt', 'schedule'],
            'learning': ['education', 'study', 'knowledge', 'skill', 'training', 'course'],
            'business': ['work', 'company', 'corporate', 'professional', 'career', 'job'],
            'health': ['wellness', 'fitness', 'medical', 'doctor', 'exercise', 'nutrition'],
            'technology': ['tech', 'digital', 'computer', 'software', 'hardware', 'internet'],
            'finance': ['money', 'budget', 'investment', 'financial', 'banking', 'economy'],
            'travel': ['trip', 'vacation', 'journey', 'tourism', 'flight', 'hotel'],
        }
        
        # Word importance weights
        self.word_weights = {
            'important': 2.0,
            'urgent': 2.0,
            'critical': 2.0,
            'priority': 1.5,
            'key': 1.5,
            'main': 1.5,
            'primary': 1.5,
        }
        
        logger.info("✅ Ultra-basic semantic search initialized (pure Python)")
    
    async def index_content(self, user_id: str, content_items: List[Dict]) -> Dict:
        """Index content for basic semantic search."""
        try:
            indexed_count = 0
            
            for item in content_items:
                content_id = item.get('id')
                if not content_id:
                    continue
                
                # Create searchable text
                searchable_text = self._create_searchable_text(item)
                processed_words = self._extract_keywords(searchable_text)
                
                # Store in index
                self.content_index[content_id] = processed_words
                self.content_metadata[content_id] = {
                    'user_id': user_id,
                    'content_type': item.get('content_type'),
                    'title': item.get('title', ''),
                    'created_at': item.get('created_at'),
                    'original_text': searchable_text
                }
                
                indexed_count += 1
            
            logger.info(f"📚 Indexed {indexed_count} items for basic semantic search")
            
            return {
                "success": True,
                "indexed_count": indexed_count,
                "total_content": len(self.content_index)
            }
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return {"success": False, "error": str(e)}
    
    async def semantic_search(self, user_id: str, query: str, limit: int = 10, similarity_threshold: float = 0.1) -> Dict:
        """Perform basic semantic search."""
        try:
            if not self.content_index:
                return {"success": True, "results": [], "count": 0}
            
            # Extract keywords from query
            query_keywords = self._extract_keywords(query)
            expanded_keywords = self._expand_with_synonyms(query_keywords)
            
            # Calculate scores for each document
            scores = []
            
            for content_id, doc_keywords in self.content_index.items():
                metadata = self.content_metadata.get(content_id, {})
                
                # Filter by user
                if metadata.get('user_id') != user_id:
                    continue
                
                # Calculate similarity score
                similarity = self._calculate_basic_similarity(expanded_keywords, doc_keywords)
                
                if similarity >= similarity_threshold:
                    scores.append({
                        'content_id': content_id,
                        'similarity_score': similarity,
                        'metadata': metadata
                    })
            
            # Sort by similarity and limit
            scores.sort(key=lambda x: x['similarity_score'], reverse=True)
            top_results = scores[:limit]
            
            # Enhance results
            enhanced_results = self._enhance_search_results(top_results, query)
            
            return {
                "success": True,
                "results": enhanced_results,
                "count": len(enhanced_results),
                "query": query,
                "search_type": "basic_semantic"
            }
            
        except Exception as e:
            logger.error(f"Basic semantic search error: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_searchable_text(self, item: Dict) -> str:
        """Create searchable text from content item."""
        parts = []
        
        # Add title with higher weight
        title = item.get('title', '').strip()
        if title:
            parts.append(f"{title} {title} {title}")  # Triple for high weight
        
        # Add content
        content = item.get('content', '').strip()
        if content:
            parts.append(content)
        
        # Add URL for links
        if item.get('content_type') == 'link':
            url = item.get('url', '').strip()
            if url:
                parts.append(url)
        
        return ' '.join(parts).strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using pure Python."""
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Common stop words to remove
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'myself', 'yourself',
            'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'
        }
        
        # Filter words
        keywords = []
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        return keywords
    
    def _expand_with_synonyms(self, keywords: List[str]) -> List[str]:
        """Expand keywords with synonyms."""
        expanded = list(keywords)
        
        for keyword in keywords:
            if keyword in self.synonyms:
                for synonym_phrase in self.synonyms[keyword]:
                    synonym_words = self._extract_keywords(synonym_phrase)
                    expanded.extend(synonym_words)
        
        return list(set(expanded))  # Remove duplicates
    
    def _calculate_basic_similarity(self, query_keywords: List[str], doc_keywords: List[str]) -> float:
        """Calculate basic similarity score."""
        if not query_keywords or not doc_keywords:
            return 0.0
        
        # Count matches
        query_set = set(query_keywords)
        doc_set = set(doc_keywords)
        
        # Exact matches
        exact_matches = len(query_set & doc_set)
        
        # Partial matches (word contains another word)
        partial_matches = 0
        for q_word in query_keywords:
            for d_word in doc_keywords:
                if len(q_word) > 3 and len(d_word) > 3:
                    if q_word in d_word or d_word in q_word:
                        partial_matches += 0.5
        
        # Calculate base similarity
        total_query_words = len(query_set)
        similarity = (exact_matches + partial_matches) / total_query_words
        
        # Apply word importance weights
        weighted_score = 0
        for word in query_keywords:
            if word in doc_keywords:
                weight = self.word_weights.get(word, 1.0)
                weighted_score += weight
        
        # Combine scores
        final_score = (similarity * 0.7) + (weighted_score / total_query_words * 0.3)
        
        return min(final_score, 1.0)  # Cap at 1.0
    
    def _enhance_search_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Enhance search results with snippets."""
        enhanced_results = []
        
        for result in results:
            content_id = result['content_id']
            metadata = result['metadata']
            
            # Create snippet
            original_text = metadata.get('original_text', '')
            snippet = self._create_snippet(original_text, query)
            
            enhanced_result = {
                'id': content_id,
                'title': metadata.get('title', 'Untitled'),
                'content_type': metadata.get('content_type', 'unknown'),
                'snippet': snippet,
                'similarity_score': result['similarity_score'],
                'created_at': metadata.get('created_at'),
                'search_type': 'basic_semantic'
            }
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _create_snippet(self, text: str, query: str, max_length: int = 150) -> str:
        """Create snippet with query context."""
        if not text:
            return ""
        
        query_keywords = self._extract_keywords(query)
        text_lower = text.lower()
        
        # Find best position with most query matches
        best_pos = 0
        max_matches = 0
        
        # Try different positions
        step = max(20, len(text) // 10)
        for i in range(0, max(1, len(text) - max_length), step):
            snippet = text_lower[i:i + max_length]
            matches = sum(1 for word in query_keywords if word in snippet)
            if matches > max_matches:
                max_matches = matches
                best_pos = i
        
        # Extract snippet
        snippet = text[best_pos:best_pos + max_length].strip()
        
        # Add ellipsis
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(text):
            snippet = snippet + "..."
        
        return snippet

# Global basic engine
basic_engine = None

def get_basic_engine() -> BasicSemanticEngine:
    """Get global basic semantic engine."""
    global basic_engine
    if basic_engine is None:
        basic_engine = BasicSemanticEngine()
    return basic_engine

async def basic_semantic_search(user_id: str, query: str, limit: int = 10) -> Dict:
    """Perform basic semantic search."""
    engine = get_basic_engine()
    return await engine.semantic_search(user_id, query, limit)

async def index_user_content_basic(user_id: str, content_items: List[Dict]) -> Dict:
    """Index content for basic search."""
    engine = get_basic_engine()
    return await engine.index_content(user_id, content_items)
