"""
Enhanced Semantic Search Engine with Memory-Optimized ML
Uses scikit-learn for better search without heavy dependencies
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedSemanticEngine:
    """Memory-optimized semantic search with scikit-learn"""
    
    def __init__(self):
        self.content_index = {}
        self.content_metadata = {}
        self.vectorizer = None
        self.content_vectors = None
        self.content_ids = []
        
        # Enhanced synonyms for better AI/GPT search
        self.synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'deep learning', 'neural', 'algorithm', 'gpt', 'chatgpt', 'openai', 'llm', 'language model'],
            'gpt': ['ai', 'artificial intelligence', 'chatgpt', 'openai', 'language model', 'llm', 'generative'],
            'chatgpt': ['ai', 'gpt', 'openai', 'artificial intelligence', 'language model', 'conversational ai'],
            'programming': ['coding', 'development', 'software', 'code', 'dev', 'tech', 'computer', 'python', 'javascript'],
            'productivity': ['efficiency', 'time management', 'organization', 'workflow', 'optimization', 'performance'],
            'learning': ['education', 'study', 'knowledge', 'skill', 'training', 'course', 'tutorial'],
            'task': ['todo', 'work', 'assignment', 'job', 'project', 'activity', 'reminder'],
            'note': ['information', 'data', 'knowledge', 'content', 'memo', 'record', 'save'],
        }
        
        self._initialize_vectorizer()
    
    def _initialize_vectorizer(self):
        """Initialize TF-IDF vectorizer with scikit-learn"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Store for later use
            self.cosine_similarity = cosine_similarity
            self.np = np
            
            # Enhanced TF-IDF with better parameters
            self.vectorizer = TfidfVectorizer(
                max_features=5000,      # Limit features for memory
                stop_words='english',   # Remove common words
                ngram_range=(1, 2),     # Include bigrams
                min_df=1,               # Include rare terms
                max_df=0.95,            # Remove too common terms
                lowercase=True,
                strip_accents='ascii'
            )
            
            logger.info("✅ Enhanced semantic engine initialized with scikit-learn")
            return True
            
        except ImportError:
            logger.warning("⚠️ scikit-learn not available, falling back to basic search")
            return False
    
    async def index_content(self, content_data: List[Dict]) -> bool:
        """Index content with enhanced preprocessing"""
        try:
            if not self.vectorizer:
                return False
                
            # Prepare content for indexing
            documents = []
            self.content_ids = []
            self.content_metadata = {}
            
            for item in content_data:
                content_id = item.get('id')
                if not content_id:
                    continue
                    
                # Enhanced content processing
                text_parts = []
                
                # Title (weighted higher)
                title = item.get('title', '')
                if title:
                    text_parts.append(f"{title} {title}")  # Duplicate for weight
                
                # Content
                content = item.get('content', '')
                if content:
                    text_parts.append(content)
                
                # URL title
                url_title = item.get('url_title', '')
                if url_title and url_title != title:
                    text_parts.append(url_title)
                
                # Tags
                tags = item.get('tags', [])
                if tags:
                    text_parts.append(' '.join(tags))
                
                # Category
                category = item.get('category', '')
                if category:
                    text_parts.append(category)
                
                # Combine all text
                full_text = ' '.join(text_parts)
                
                # Apply synonym expansion
                full_text = self._expand_synonyms(full_text)
                
                documents.append(full_text)
                self.content_ids.append(content_id)
                self.content_metadata[content_id] = item
            
            if not documents:
                logger.warning("No content to index")
                return False
            
            # Create TF-IDF vectors
            self.content_vectors = self.vectorizer.fit_transform(documents)
            
            logger.info(f"✅ Indexed {len(documents)} documents with enhanced semantic search")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to index content: {e}")
            return False
    
    def _expand_synonyms(self, text: str) -> str:
        """Expand text with synonyms for better matching"""
        text_lower = text.lower()
        expanded_parts = [text]
        
        for key, synonyms in self.synonyms.items():
            if key in text_lower:
                expanded_parts.extend(synonyms)
        
        return ' '.join(expanded_parts)
    
    async def search(self, query: str, limit: int = 10, min_score: float = 0.1) -> List[Dict]:
        """Enhanced semantic search with better scoring"""
        try:
            if not self.vectorizer or self.content_vectors is None:
                logger.warning("Search engine not properly initialized")
                return []
            
            # Preprocess query
            query = self._expand_synonyms(query.lower())
            
            # Create query vector
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = self.cosine_similarity(query_vector, self.content_vectors)[0]
            
            # Get top results
            results = []
            for idx, score in enumerate(similarities):
                if score >= min_score:
                    content_id = self.content_ids[idx]
                    metadata = self.content_metadata.get(content_id, {})
                    
                    results.append({
                        'id': content_id,
                        'score': float(score),
                        'title': metadata.get('title', 'Untitled'),
                        'content': metadata.get('content', ''),
                        'url': metadata.get('url', ''),
                        'content_type': metadata.get('content_type', 'unknown'),
                        'created_at': metadata.get('created_at', ''),
                        'tags': metadata.get('tags', [])
                    })
            
            # Sort by score (descending)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Apply limit
            results = results[:limit]
            
            logger.info(f"🔍 Enhanced search for '{query}' found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Enhanced search failed: {e}")
            return []
    
    def get_related_content(self, content_id: str, limit: int = 5) -> List[Dict]:
        """Find content related to a specific item"""
        try:
            if content_id not in self.content_ids:
                return []
            
            # Get the index of this content
            idx = self.content_ids.index(content_id)
            content_vector = self.content_vectors[idx:idx+1]
            
            # Find similar content
            similarities = self.cosine_similarity(content_vector, self.content_vectors)[0]
            
            # Get related items (excluding self)
            related = []
            for i, score in enumerate(similarities):
                if i != idx and score > 0.2:  # Exclude self and low scores
                    related_id = self.content_ids[i]
                    metadata = self.content_metadata.get(related_id, {})
                    
                    related.append({
                        'id': related_id,
                        'score': float(score),
                        'title': metadata.get('title', 'Untitled'),
                        'content_type': metadata.get('content_type', 'unknown')
                    })
            
            # Sort and limit
            related.sort(key=lambda x: x['score'], reverse=True)
            return related[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to find related content: {e}")
            return []

def get_enhanced_engine():
    """Factory function to create enhanced semantic engine"""
    return EnhancedSemanticEngine()

# Memory usage monitoring
def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        return memory_mb
    except ImportError:
        return 0

def log_memory_usage(context: str = ""):
    """Log current memory usage"""
    memory_mb = get_memory_usage()
    if memory_mb > 0:
        percentage = (memory_mb / 512) * 100
        logger.info(f"💾 Memory usage {context}: {memory_mb:.1f}MB / 512MB ({percentage:.1f}%)")
    return memory_mb
