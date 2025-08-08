#!/usr/bin/env python3
"""
🔍 Advanced Search Engine for MySecondMind

Centralized search functionality with multiple search methods:
- PostgreSQL Full-Text Search
- Keyword preprocessing and expansion
- Future: Semantic search with embeddings
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result with relevance scoring."""
    content_id: str
    title: str
    content: str
    content_type: str
    created_at: str
    relevance_score: float = 0.0
    snippet: str = ""

class SearchEngine:
    """Advanced search engine with multiple search strategies."""
    
    def __init__(self, content_handler):
        self.content_handler = content_handler
        
        # Synonym mappings for query expansion
        self.synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'deep learning'],
            'crypto': ['cryptocurrency', 'bitcoin', 'blockchain', 'btc', 'ethereum'],
            'productivity': ['efficiency', 'time management', 'organization', 'workflow'],
            'ocean': ['sea', 'marine', 'water', 'aquatic'],
            'solar': ['renewable energy', 'photovoltaic', 'green energy', 'sustainable'],
            # URL domain mappings for link searches
            'youtube': ['youtube.com', 'youtu.be', 'video', 'watch'],
            'instagram': ['instagram.com', 'insta', 'ig', 'reel', 'post'],
            'twitter': ['twitter.com', 'x.com', 'tweet'],
            'github': ['github.com', 'git', 'repository', 'repo', 'code'],
            'linkedin': ['linkedin.com', 'professional', 'career'],
            'medium': ['medium.com', 'article', 'blog post'],
        }
        
        # Common abbreviations
        self.abbreviations = {
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'dl': 'deep learning',
            'api': 'application programming interface',
            'ui': 'user interface',
            'ux': 'user experience',
        }
    
    async def search(self, user_id: str, query: str, limit: int = 10) -> Dict:
        """Main search interface with multiple strategies."""
        try:
            # Step 1: Preprocess query
            processed_query = self._preprocess_query(query)
            
            # Step 2: Try PostgreSQL full-text search first
            results = await self._fulltext_search(user_id, processed_query, limit)
            
            # Step 3: If no results, try expanded query
            if not results.get('results'):
                expanded_query = self._expand_query(processed_query)
                if expanded_query != processed_query:
                    results = await self._fulltext_search(user_id, expanded_query, limit)
            
            # Step 4: If still no results, try fuzzy search
            if not results.get('results'):
                results = await self._fuzzy_search(user_id, query, limit)
            
            # Step 5: Post-process results
            if results.get('results'):
                results['results'] = self._rank_and_format_results(results['results'], query)
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"success": False, "error": "Search failed", "results": []}
    
    def _preprocess_query(self, query: str) -> str:
        """Clean and preprocess search query."""
        # Convert to lowercase
        query = query.lower().strip()
        
        # Remove common stop words for search
        stop_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        words = query.split()
        words = [word for word in words if word not in stop_words]
        
        # Expand abbreviations
        expanded_words = []
        for word in words:
            if word in self.abbreviations:
                expanded_words.append(f"{word} {self.abbreviations[word]}")
            else:
                expanded_words.append(word)
        
        return " ".join(expanded_words)
    
    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms."""
        words = query.split()
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            
            # Add synonyms
            if word in self.synonyms:
                expanded_words.extend(self.synonyms[word])
        
        return " ".join(expanded_words)
    
    async def _fulltext_search(self, user_id: str, query: str, limit: int) -> Dict:
        """PostgreSQL full-text search."""
        try:
            return await self.content_handler.search_content(user_id, query, limit)
        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            return {"success": False, "results": []}
    
    async def _fuzzy_search(self, user_id: str, query: str, limit: int) -> Dict:
        """Fuzzy search with typo tolerance."""
        try:
            # Get all user content
            all_content = await self.content_handler.get_user_content(user_id, limit=100)
            
            if not all_content.get("success"):
                return all_content
            
            # Simple fuzzy matching
            results = []
            query_words = query.lower().split()
            
            for item in all_content["content"]:
                title = item.get('title', '').lower()
                content = item.get('content', '').lower()
                
                # Calculate match score
                score = 0
                for word in query_words:
                    # Exact match (high score)
                    if word in title:
                        score += 10
                    if word in content:
                        score += 5
                    
                    # Fuzzy match (lower score)
                    for content_word in (title + " " + content).split():
                        if self._fuzzy_match(word, content_word):
                            score += 2
                
                if score > 0:
                    item['relevance_score'] = score
                    results.append(item)
            
            # Sort by relevance score
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return {
                "success": True,
                "results": results[:limit],
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return {"success": False, "results": []}
    
    def _fuzzy_match(self, word1: str, word2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy string matching."""
        if len(word1) < 3 or len(word2) < 3:
            return False
        
        # Simple Levenshtein-like comparison
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        # Check for common prefixes/suffixes
        if word1[:3] == word2[:3]:  # Same start
            return True
        if word1[-3:] == word2[-3:]:  # Same end
            return True
        
        # Check character overlap
        overlap = len(set(word1) & set(word2))
        min_len = min(len(word1), len(word2))
        
        return (overlap / min_len) >= threshold
    
    def _rank_and_format_results(self, results: List[Dict], original_query: str) -> List[Dict]:
        """Rank results and add snippets."""
        formatted_results = []
        query_words = original_query.lower().split()
        
        for item in results:
            # Create snippet with highlighted terms
            content = item.get('content', '')
            snippet = self._create_snippet(content, query_words)
            
            formatted_item = {
                **item,
                'snippet': snippet,
                'relevance_score': item.get('relevance_score', 0)
            }
            formatted_results.append(formatted_item)
        
        return formatted_results
    
    def _create_snippet(self, content: str, query_words: List[str], max_length: int = 150) -> str:
        """Create a snippet with context around matching terms."""
        if not content:
            return ""
        
        content_lower = content.lower()
        
        # Find the best snippet position
        best_pos = 0
        max_matches = 0
        
        # Look for positions with most query word matches
        for i in range(0, len(content) - max_length, 20):
            snippet = content_lower[i:i + max_length]
            matches = sum(1 for word in query_words if word in snippet)
            if matches > max_matches:
                max_matches = matches
                best_pos = i
        
        # Extract snippet
        snippet = content[best_pos:best_pos + max_length]
        
        # Clean up snippet boundaries
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(content):
            snippet = snippet + "..."
        
        return snippet.strip()

# Global search engine instance
search_engine = None

def get_search_engine():
    """Get the global search engine instance."""
    global search_engine
    if search_engine is None:
        from handlers.supabase_content import content_handler
        search_engine = SearchEngine(content_handler)
    return search_engine
