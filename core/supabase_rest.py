#!/usr/bin/env python3
"""
🔧 Custom Supabase REST Client

This module provides a simple REST client for Supabase that bypasses
the Python client library version conflicts.
"""

import os
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SupabaseRestClient:
    """Simple REST client for Supabase operations."""
    
    def __init__(self):
        self.base_url = os.getenv('SUPABASE_URL')
        # Prefer service role if provided (server-side only), fallback to anon key
        service_key = os.getenv('SUPABASE_SERVICE_ROLE')
        anon_key = os.getenv('SUPABASE_ANON_KEY')
        self.api_key = service_key or anon_key
        
        if not self.base_url or not self.api_key:
            logger.error("❌ SUPABASE_URL and API key (SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY) required")
            self.ready = False
            return
            
        self.rest_url = f"{self.base_url}/rest/v1"
        self.headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            # Ask PostgREST to return affected rows for mutations
            'Prefer': 'return=representation'
        }
        self.ready = True
        logger.info("✅ Supabase REST client initialized")
        if service_key:
            logger.info("🔐 Using service role key for Supabase requests")
    
    def table(self, table_name: str):
        """Get a table operation object."""
        return SupabaseTable(self, table_name)

class SupabaseTable:
    """Table operations for Supabase REST API."""
    
    def __init__(self, client: SupabaseRestClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self.base_url = f"{client.rest_url}/{table_name}"
    
    def insert(self, data: Dict) -> 'SupabaseQuery':
        """Insert data into table."""
        return SupabaseQuery(self, 'POST', data=data)
    
    def select(self, columns: str = "*") -> 'SupabaseQuery':
        """Select data from table."""
        query = SupabaseQuery(self, 'GET')
        query.columns = columns
        return query
    
    def update(self, data: Dict) -> 'SupabaseQuery':
        """Update data in table."""
        return SupabaseQuery(self, 'PATCH', data=data)
    
    def delete(self) -> 'SupabaseQuery':
        """Delete data from table."""
        return SupabaseQuery(self, 'DELETE')

class SupabaseQuery:
    """Query builder for Supabase operations."""
    
    def __init__(self, table: SupabaseTable, method: str, data: Optional[Dict] = None):
        self.table = table
        self.method = method
        self.data = data
        self.columns = "*"
        self.filters = []
        self.order_by = None
        self.limit_count = None
    
    def eq(self, column: str, value: Any) -> 'SupabaseQuery':
        """Add equality filter."""
        # Quote string values that may include special characters
        value_str = str(value)
        self.filters.append(f"{column}=eq.{value_str}")
        return self
    
    def order(self, column: str, desc: bool = False) -> 'SupabaseQuery':
        """Add ordering."""
        direction = "desc" if desc else "asc"
        self.order_by = f"{column}.{direction}"
        return self
    
    def limit(self, count: int) -> 'SupabaseQuery':
        """Limit results."""
        self.limit_count = count
        return self
    
    def text_search(self, column: str, query: str) -> 'SupabaseQuery':
        """Add text search filter (PostgreSQL full-text search)."""
        self.filters.append(f"{column}=fts.{query}")
        return self
    
    def or_(self, filter_string: str) -> 'SupabaseQuery':
        """Add OR filter."""
        self.filters.append(f"or=({filter_string})")
        return self
    
    def _build_params(self) -> Dict[str, Any]:
        """Build query params for any HTTP method."""
        params: Dict[str, Any] = {}
        # Always send select for representation when not GET as well
        params['select'] = self.columns
        
        # Apply filters
        for filter_str in self.filters:
            if filter_str.startswith('or='):
                # 'or' is already a key
                key, value = filter_str.split('=', 1)
                params[key] = value
            else:
                key, value = filter_str.split('=', 1)
                params[key] = value
        
        if self.order_by:
            params['order'] = self.order_by
        if self.limit_count is not None:
            params['limit'] = self.limit_count
        return params
    
    def execute(self) -> Dict:
        """Execute the query."""
        if not self.table.client.ready:
            return {"data": None, "error": "Client not ready"}
        
        url = self.table.base_url
        params = self._build_params()
        
        try:
            if self.method == 'GET':
                response = requests.get(url, headers=self.table.client.headers, params=params, timeout=10)
            elif self.method == 'POST':
                response = requests.post(url, headers=self.table.client.headers, json=self.data, params=params, timeout=10)
            elif self.method == 'PATCH':
                response = requests.patch(url, headers=self.table.client.headers, json=self.data, params=params, timeout=10)
            elif self.method == 'DELETE':
                response = requests.delete(url, headers=self.table.client.headers, params=params, timeout=10)
            else:
                return {"data": None, "error": f"Unsupported method: {self.method}"}
            
            # Supabase PostgREST returns 200 with body for mutations when Prefer return=representation
            if response.status_code in [200, 201]:
                data = response.json() if response.content else []
                return {"data": data, "error": None}
            elif response.status_code == 204:
                # No content returned (e.g., delete without representation)
                return {"data": [], "error": None}
            else:
                return {"data": None, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return {"data": None, "error": str(e)}

# Create global client instance
supabase_rest = SupabaseRestClient()
