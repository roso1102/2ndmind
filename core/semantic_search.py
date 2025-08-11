#!/usr/bin/env python3
"""
🔍 Advanced Semantic Search Engine for MySecondMind

This module provides semantic search capabilities using:
- Sentence-transformers for embeddings (free, local)
- FAISS for fast vector similarity search
- Intelligent query expansion and reranking
- Content clustering and recommendations
"""

import os
import json
import logging
import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import pickle

logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Semantic search disabled.")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not available. Vector search will use basic similarity.")

class SemanticSearchEngine:
    """Advanced semantic search with embeddings and vector similarity."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.faiss_index = None
        self.content_embeddings = {}  # content_id -> embedding
        self.content_metadata = {}    # content_id -> metadata
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Initialize model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.embedding_dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"✅ Semantic search initialized with {model_name} (dim: {self.embedding_dimension})")
            except Exception as e:
                logger.error(f"❌ Failed to load sentence transformer: {e}")
                self.model = None
        
        # Initialize FAISS index
        if FAISS_AVAILABLE and self.model:
            try:
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product (cosine similarity)
                logger.info("✅ FAISS index initialized for vector search")
            except Exception as e:
                logger.error(f"❌ Failed to initialize FAISS: {e}")
                self.faiss_index = None
    
    async def index_content(self, user_id: str, content_items: List[Dict]) -> Dict:
        """Index content items for semantic search."""
        if not self.model:
            return {"success": False, "error": "Semantic search not available"}
        
        try:
            indexed_count = 0
            
            for item in content_items:
                content_id = item.get('id')
                if not content_id:
                    continue
                
                # Create searchable text
                searchable_text = self._create_searchable_text(item)
                
                # Generate embedding
                embedding = await self._generate_embedding(searchable_text)
                if embedding is not None:
                    # Store embedding and metadata
                    self.content_embeddings[content_id] = embedding
                    self.content_metadata[content_id] = {
                        'user_id': user_id,
                        'content_type': item.get('content_type'),
                        'title': item.get('title', ''),
                        'created_at': item.get('created_at'),
                        'searchable_text': searchable_text
                    }
                    indexed_count += 1
            
            # Rebuild FAISS index if available
            if self.faiss_index and indexed_count > 0:
                await self._rebuild_faiss_index()
            
            logger.info(f"📚 Indexed {indexed_count} items for semantic search")
            
            return {
                "success": True,
                "indexed_count": indexed_count,
                "total_embeddings": len(self.content_embeddings)
            }
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return {"success": False, "error": str(e)}
    
    async def semantic_search(self, user_id: str, query: str, limit: int = 10, similarity_threshold: float = 0.3) -> Dict:
        """Perform semantic search using embeddings."""
        if not self.model:
            return {"success": False, "error": "Semantic search not available"}
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            if query_embedding is None:
                return {"success": False, "error": "Failed to generate query embedding"}
            
            # Find similar content
            if self.faiss_index and len(self.content_embeddings) > 0:
                results = await self._faiss_search(user_id, query_embedding, limit, similarity_threshold)
            else:
                results = await self._manual_similarity_search(user_id, query_embedding, limit, similarity_threshold)
            
            # Enhance results with snippets and ranking
            enhanced_results = await self._enhance_search_results(results, query)
            
            return {
                "success": True,
                "results": enhanced_results,
                "count": len(enhanced_results),
                "query": query,
                "search_type": "semantic"
            }
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text."""
        if not self.model or not text.strip():
            return None
        
        try:
            # Clean and prepare text
            text = text.strip()[:1000]  # Limit length
            
            # Generate embedding
            embedding = self.model.encode(text, convert_to_tensor=False, normalize_embeddings=True)
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    def _create_searchable_text(self, item: Dict) -> str:
        """Create searchable text from content item."""
        parts = []
        
        # Add title with higher weight
        title = item.get('title', '').strip()
        if title:
            parts.append(f"{title} {title}")  # Duplicate title for higher weight
        
        # Add content
        content = item.get('content', '').strip()
        if content:
            parts.append(content)
        
        # Add URL for links
        if item.get('content_type') == 'link':
            url = item.get('url', '').strip()
            if url:
                parts.append(url)
        
        # Add tags if available
        tags = item.get('tags', [])
        if tags:
            parts.extend(tags)
        
        return ' '.join(parts).strip()
    
    async def _rebuild_faiss_index(self) -> None:
        """Rebuild FAISS index with current embeddings."""
        if not self.faiss_index or not self.content_embeddings:
            return
        
        try:
            # Reset index
            self.faiss_index.reset()
            
            # Prepare embeddings matrix
            embeddings_list = list(self.content_embeddings.values())
            embeddings_matrix = np.vstack(embeddings_list)
            
            # Add to index
            self.faiss_index.add(embeddings_matrix)
            
            logger.info(f"🔄 FAISS index rebuilt with {len(embeddings_list)} embeddings")
            
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
    
    async def _faiss_search(self, user_id: str, query_embedding: np.ndarray, limit: int, threshold: float) -> List[Dict]:
        """Search using FAISS index."""
        if not self.faiss_index or len(self.content_embeddings) == 0:
            return []
        
        try:
            # Search for similar vectors
            query_vector = query_embedding.reshape(1, -1)
            scores, indices = self.faiss_index.search(query_vector, min(limit * 2, len(self.content_embeddings)))
            
            # Convert results
            results = []
            content_ids = list(self.content_embeddings.keys())
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or score < threshold:  # FAISS returns -1 for invalid results
                    continue
                
                content_id = content_ids[idx]
                metadata = self.content_metadata.get(content_id, {})
                
                # Filter by user
                if metadata.get('user_id') != user_id:
                    continue
                
                results.append({
                    'content_id': content_id,
                    'similarity_score': float(score),
                    'metadata': metadata
                })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return []
    
    async def _manual_similarity_search(self, user_id: str, query_embedding: np.ndarray, limit: int, threshold: float) -> List[Dict]:
        """Manual similarity search when FAISS is not available."""
        try:
            results = []
            
            for content_id, embedding in self.content_embeddings.items():
                metadata = self.content_metadata.get(content_id, {})
                
                # Filter by user
                if metadata.get('user_id') != user_id:
                    continue
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                )
                
                if similarity >= threshold:
                    results.append({
                        'content_id': content_id,
                        'similarity_score': float(similarity),
                        'metadata': metadata
                    })
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Manual similarity search error: {e}")
            return []
    
    async def _enhance_search_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Enhance search results with additional information."""
        enhanced_results = []
        
        for result in results:
            content_id = result['content_id']
            metadata = result['metadata']
            
            # Create snippet from searchable text
            searchable_text = metadata.get('searchable_text', '')
            snippet = self._create_snippet(searchable_text, query)
            
            enhanced_result = {
                'id': content_id,
                'title': metadata.get('title', 'Untitled'),
                'content_type': metadata.get('content_type', 'unknown'),
                'snippet': snippet,
                'similarity_score': result['similarity_score'],
                'created_at': metadata.get('created_at'),
                'search_type': 'semantic'
            }
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _create_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Create a snippet highlighting relevant parts."""
        if not text:
            return ""
        
        # Simple snippet creation - find best matching part
        text_lower = text.lower()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Find the position with most query word matches
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
        
        # Add ellipsis if needed
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    async def get_content_recommendations(self, user_id: str, content_id: str, limit: int = 5) -> List[Dict]:
        """Get content recommendations based on similarity to given content."""
        if not self.model or content_id not in self.content_embeddings:
            return []
        
        try:
            # Get embedding for the reference content
            reference_embedding = self.content_embeddings[content_id]
            
            # Find similar content
            results = await self._manual_similarity_search(user_id, reference_embedding, limit + 1, 0.4)
            
            # Remove the reference content itself
            results = [r for r in results if r['content_id'] != content_id]
            
            return await self._enhance_search_results(results[:limit], "")
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    async def cluster_user_content(self, user_id: str, num_clusters: int = 5) -> Dict:
        """Cluster user content based on semantic similarity."""
        if not self.model or not FAISS_AVAILABLE:
            return {"success": False, "error": "Clustering not available"}
        
        try:
            # Get user embeddings
            user_embeddings = []
            user_content_ids = []
            
            for content_id, metadata in self.content_metadata.items():
                if metadata.get('user_id') == user_id:
                    user_embeddings.append(self.content_embeddings[content_id])
                    user_content_ids.append(content_id)
            
            if len(user_embeddings) < num_clusters:
                return {"success": False, "error": "Not enough content for clustering"}
            
            # Perform k-means clustering
            embeddings_matrix = np.vstack(user_embeddings)
            
            # Simple k-means using FAISS
            kmeans = faiss.Kmeans(self.embedding_dimension, num_clusters)
            kmeans.train(embeddings_matrix)
            
            # Get cluster assignments
            _, cluster_assignments = kmeans.index.search(embeddings_matrix, 1)
            
            # Organize results
            clusters = {}
            for i, content_id in enumerate(user_content_ids):
                cluster_id = int(cluster_assignments[i][0])
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                
                metadata = self.content_metadata[content_id]
                clusters[cluster_id].append({
                    'content_id': content_id,
                    'title': metadata.get('title', ''),
                    'content_type': metadata.get('content_type', ''),
                })
            
            return {
                "success": True,
                "clusters": clusters,
                "num_clusters": len(clusters)
            }
            
        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return {"success": False, "error": str(e)}
    
    def save_embeddings(self, filepath: str) -> bool:
        """Save embeddings to file."""
        try:
            data = {
                'embeddings': self.content_embeddings,
                'metadata': self.content_metadata,
                'model_name': self.model_name
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"💾 Embeddings saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
            return False
    
    def load_embeddings(self, filepath: str) -> bool:
        """Load embeddings from file."""
        try:
            if not os.path.exists(filepath):
                return False
            
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.content_embeddings = data.get('embeddings', {})
            self.content_metadata = data.get('metadata', {})
            
            # Rebuild FAISS index
            if self.faiss_index and self.content_embeddings:
                asyncio.create_task(self._rebuild_faiss_index())
            
            logger.info(f"📂 Embeddings loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return False

# Global semantic search engine
semantic_engine = None

def get_semantic_engine() -> SemanticSearchEngine:
    """Get global semantic search engine instance."""
    global semantic_engine
    if semantic_engine is None:
        semantic_engine = SemanticSearchEngine()
    return semantic_engine

async def index_user_content(user_id: str, content_items: List[Dict]) -> Dict:
    """Index content for semantic search."""
    engine = get_semantic_engine()
    return await engine.index_content(user_id, content_items)

async def semantic_search(user_id: str, query: str, limit: int = 10) -> Dict:
    """Perform semantic search."""
    engine = get_semantic_engine()
    return await engine.semantic_search(user_id, query, limit)

async def get_content_recommendations(user_id: str, content_id: str, limit: int = 5) -> List[Dict]:
    """Get content recommendations."""
    engine = get_semantic_engine()
    return await engine.get_content_recommendations(user_id, content_id, limit)
