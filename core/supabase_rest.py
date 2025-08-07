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
        self.anon_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.base_url or not self.anon_key:
            logger.error("❌ SUPABASE_URL and SUPABASE_ANON_KEY required")
            self.ready = False
            return
            
        self.rest_url = f"{self.base_url}/rest/v1"
        self.headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        self.ready = True
        logger.info("✅ Supabase REST client initialized")
    
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
        self.filters.append(f"{column}=eq.{value}")
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
    
    def execute(self) -> Dict:
        """Execute the query."""
        if not self.table.client.ready:
            return {"data": None, "error": "Client not ready"}
        
        # Build URL with query parameters
        url = self.table.base_url
        params = {}
        
        if self.method == 'GET':
            params['select'] = self.columns
            
            if self.filters:
                for filter_str in self.filters:
                    key, value = filter_str.split('=', 1)
                    params[key] = value
            
            if self.order_by:
                params['order'] = self.order_by
            
            if self.limit_count:
                params['limit'] = self.limit_count
        
        try:
            if self.method == 'GET':
                response = requests.get(url, headers=self.table.client.headers, 
                                      params=params, timeout=10)
            elif self.method == 'POST':
                response = requests.post(url, headers=self.table.client.headers,
                                       json=self.data, params=params, timeout=10)
            elif self.method == 'PATCH':
                response = requests.patch(url, headers=self.table.client.headers,
                                        json=self.data, params=params, timeout=10)
            elif self.method == 'DELETE':
                response = requests.delete(url, headers=self.table.client.headers,
                                         params=params, timeout=10)
            else:
                return {"data": None, "error": f"Unsupported method: {self.method}"}
            
            if response.status_code in [200, 201]:
                data = response.json() if response.content else []
                return {"data": data, "error": None}
            else:
                return {"data": None, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return {"data": None, "error": str(e)}

# Create global client instance
supabase_rest = SupabaseRestClient()
