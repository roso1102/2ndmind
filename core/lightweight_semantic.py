#!/usr/bin/env python3
"""
🔍 Lightweight Semantic Search for MySecondMind (Under 512MB)

This module provides basic semantic search without heavy dependencies:
- Uses simple TF-IDF instead of neural embeddings
- Lightweight similarity calculations
- Still provides intelligent search capabilities
"""

import logging
import re
import math
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter, defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class LightweightSemanticEngine:
    """Lightweight semantic search using TF-IDF and word similarity."""
    
    def __init__(self):
        self.content_index = {}  # content_id -> processed text
        self.content_metadata = {}  # content_id -> metadata
        self.vocabulary = set()
        self.idf_scores = {}
        
        # Synonym mappings for better matching
        self.synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'deep learning'],
            'productivity': ['efficiency', 'time management', 'organization', 'workflow'],
            'programming': ['coding', 'development', 'software', 'code'],
            'task': ['todo', 'work', 'assignment', 'job'],
            'note': ['information', 'data', 'knowledge', 'content'],
            'reminder': ['alert', 'notification', 'memory', 'prompt'],
        }
        
        logger.info("✅ Lightweight semantic search initialized")
    
    async def index_content(self, user_id: str, content_items: List[Dict]) -> Dict:
        """Index content for lightweight semantic search."""
        try:
            indexed_count = 0
            
            for item in content_items:
                content_id = item.get('id')
                if not content_id:
                    continue
                
                # Create searchable text
                searchable_text = self._create_searchable_text(item)
                processed_text = self._preprocess_text(searchable_text)
                
                # Store in index
                self.content_index[content_id] = processed_text
                self.content_metadata[content_id] = {
                    'user_id': user_id,
                    'content_type': item.get('content_type'),
                    'title': item.get('title', ''),
                    'created_at': item.get('created_at'),
                    'original_text': searchable_text
                }
                
                # Update vocabulary
                self.vocabulary.update(processed_text)
                indexed_count += 1
            
            # Compute IDF scores
            if indexed_count > 0:
                self._compute_idf_scores()
            
            logger.info(f"📚 Indexed {indexed_count} items for lightweight semantic search")
            
            return {
                "success": True,
                "indexed_count": indexed_count,
                "total_content": len(self.content_index)
            }
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return {"success": False, "error": str(e)}
    
    async def semantic_search(self, user_id: str, query: str, limit: int = 10, similarity_threshold: float = 0.1) -> Dict:
        """Perform lightweight semantic search."""
        try:
            if not self.content_index:
                return {"success": True, "results": [], "count": 0}
            
            # Preprocess query
            query_terms = self._preprocess_text(query)
            expanded_query = self._expand_query_with_synonyms(query_terms)
            
            # Calculate TF-IDF scores for each document
            scores = []
            
            for content_id, doc_terms in self.content_index.items():
                metadata = self.content_metadata.get(content_id, {})
                
                # Filter by user
                if metadata.get('user_id') != user_id:
                    continue
                
                # Calculate similarity score
                similarity = self._calculate_similarity(expanded_query, doc_terms)
                
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
                "search_type": "lightweight_semantic"
            }
            
        except Exception as e:
            logger.error(f"Lightweight semantic search error: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_searchable_text(self, item: Dict) -> str:
        """Create searchable text from content item."""
        parts = []
        
        # Add title with higher weight
        title = item.get('title', '').strip()
        if title:
            parts.append(f"{title} {title}")  # Duplicate for weight
        
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
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text into terms."""
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Filter stop words and short words
        filtered_words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return filtered_words
    
    def _expand_query_with_synonyms(self, query_terms: List[str]) -> List[str]:
        """Expand query with synonyms."""
        expanded = list(query_terms)
        
        for term in query_terms:
            if term in self.synonyms:
                # Add synonyms
                for synonym_phrase in self.synonyms[term]:
                    synonym_words = self._preprocess_text(synonym_phrase)
                    expanded.extend(synonym_words)
        
        return list(set(expanded))  # Remove duplicates
    
    def _compute_idf_scores(self):
        """Compute IDF scores for vocabulary."""
        total_docs = len(self.content_index)
        
        # Count document frequency for each term
        doc_freq = defaultdict(int)
        for doc_terms in self.content_index.values():
            unique_terms = set(doc_terms)
            for term in unique_terms:
                doc_freq[term] += 1
        
        # Calculate IDF scores
        self.idf_scores = {}
        for term in self.vocabulary:
            df = doc_freq.get(term, 0)
            if df > 0:
                self.idf_scores[term] = math.log(total_docs / df)
            else:
                self.idf_scores[term] = 0
    
    def _calculate_similarity(self, query_terms: List[str], doc_terms: List[str]) -> float:
        """Calculate TF-IDF cosine similarity."""
        if not query_terms or not doc_terms:
            return 0.0
        
        # Calculate term frequencies
        query_tf = Counter(query_terms)
        doc_tf = Counter(doc_terms)
        
        # Get all unique terms
        all_terms = set(query_terms + doc_terms)
        
        # Calculate TF-IDF vectors
        query_vector = []
        doc_vector = []
        
        for term in all_terms:
            # Query TF-IDF
            q_tf = query_tf.get(term, 0)
            q_idf = self.idf_scores.get(term, 0)
            query_vector.append(q_tf * q_idf)
            
            # Document TF-IDF
            d_tf = doc_tf.get(term, 0)
            d_idf = self.idf_scores.get(term, 0)
            doc_vector.append(d_tf * d_idf)
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(query_vector, doc_vector))
        
        query_magnitude = math.sqrt(sum(a * a for a in query_vector))
        doc_magnitude = math.sqrt(sum(b * b for b in doc_vector))
        
        if query_magnitude == 0 or doc_magnitude == 0:
            return 0.0
        
        similarity = dot_product / (query_magnitude * doc_magnitude)
        
        # Boost score for exact word matches
        exact_matches = len(set(query_terms) & set(doc_terms))
        if exact_matches > 0:
            similarity += 0.1 * exact_matches
        
        return min(similarity, 1.0)  # Cap at 1.0
    
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
                'search_type': 'lightweight_semantic'
            }
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _create_snippet(self, text: str, query: str, max_length: int = 150) -> str:
        """Create snippet with query context."""
        if not text:
            return ""
        
        query_words = self._preprocess_text(query)
        text_lower = text.lower()
        
        # Find best position with most query matches
        best_pos = 0
        max_matches = 0
        
        for i in range(0, len(text) - max_length, 20):
            snippet = text_lower[i:i + max_length]
            matches = sum(1 for word in query_words if word in snippet)
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

# Global lightweight engine
lightweight_engine = None

def get_lightweight_engine() -> LightweightSemanticEngine:
    """Get global lightweight semantic engine."""
    global lightweight_engine
    if lightweight_engine is None:
        lightweight_engine = LightweightSemanticEngine()
    return lightweight_engine

async def lightweight_semantic_search(user_id: str, query: str, limit: int = 10) -> Dict:
    """Perform lightweight semantic search."""
    engine = get_lightweight_engine()
    return await engine.semantic_search(user_id, query, limit)

async def index_user_content_lightweight(user_id: str, content_items: List[Dict]) -> Dict:
    """Index content for lightweight search."""
    engine = get_lightweight_engine()
    return await engine.index_content(user_id, content_items)
