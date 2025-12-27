import os
import json
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

from config import Config

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_RAG_CONFIG = {
    'mode': 'local',           # 'local', 'server', or 'cloud'
    'local_path': '',          # Path for PersistentClient
    'server_host': 'localhost',
    'server_port': 8000,
    'cloud_tenant': '',        # Tenant ID for CloudClient
    'cloud_database': '',      # Database name for CloudClient
}


class RagConfigService:
    """Service for managing RAG/ChromaDB configuration."""

    def __init__(self):
        self._config = None
        self._config_mtime = None

    def _get_config_path(self):
        """Get path to rag_config.json in project root."""
        return Path(__file__).parent.parent / "rag_config.json"

    def get_config(self, request_id=None):
        """Load RAG configuration from file, with caching."""
        log_prefix = f"[{request_id}] " if request_id else ""
        config_path = self._get_config_path()

        # Return default if file doesn't exist
        if not config_path.exists():
            logger.debug(f"{log_prefix}No config file, using defaults")
            return DEFAULT_RAG_CONFIG.copy()

        try:
            mtime = config_path.stat().st_mtime

            # Return cached config if file unchanged
            if self._config is not None and self._config_mtime == mtime:
                return self._config.copy()

            # Load from file
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                self._config_mtime = mtime

            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_RAG_CONFIG.copy()
            merged.update(self._config)
            self._config = merged

            logger.debug(f"{log_prefix}Loaded RAG config from {config_path}")
            return self._config.copy()

        except Exception as e:
            logger.error(f"{log_prefix}Failed to load RAG config: {e}")
            return DEFAULT_RAG_CONFIG.copy()

    def save_config(self, config_data, request_id=None):
        """Save RAG configuration to file."""
        log_prefix = f"[{request_id}] " if request_id else ""
        config_path = self._get_config_path()

        # Validate required fields based on mode
        mode = config_data.get('mode', 'local')
        if mode == 'local' and not config_data.get('local_path'):
            return {'error': 'Local path is required for local mode'}
        if mode == 'server':
            if not config_data.get('server_host'):
                return {'error': 'Host is required for server mode'}
            if not config_data.get('server_port'):
                return {'error': 'Port is required for server mode'}
        if mode == 'cloud':
            if not config_data.get('cloud_tenant'):
                return {'error': 'Tenant ID is required for cloud mode'}
            if not config_data.get('cloud_database'):
                return {'error': 'Database name is required for cloud mode'}

        # Build config object
        config = {
            'mode': mode,
            'local_path': config_data.get('local_path', ''),
            'server_host': config_data.get('server_host', 'localhost'),
            'server_port': int(config_data.get('server_port', 8000)),
            'cloud_tenant': config_data.get('cloud_tenant', ''),
            'cloud_database': config_data.get('cloud_database', ''),
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            # Invalidate cache
            self._config = None
            self._config_mtime = None

            logger.info(f"{log_prefix}Saved RAG config to {config_path}")
            return {'success': True, 'config': config}

        except Exception as e:
            logger.error(f"{log_prefix}Failed to save RAG config: {e}")
            return {'error': f'Failed to save config: {str(e)}'}

    def validate_local_path(self, path, request_id=None):
        """Validate that a local path exists and is suitable for ChromaDB."""
        log_prefix = f"[{request_id}] " if request_id else ""

        if not path:
            return {'valid': False, 'message': 'Path is required'}

        path_obj = Path(path)

        # Check if path exists
        if not path_obj.exists():
            # Check if parent exists (path could be created)
            if path_obj.parent.exists():
                return {
                    'valid': True,
                    'message': 'Directory will be created',
                    'details': {'exists': False, 'will_create': True}
                }
            return {
                'valid': False,
                'message': 'Parent directory does not exist',
                'details': {'exists': False, 'parent_exists': False}
            }

        # Check if it's a directory
        if not path_obj.is_dir():
            return {
                'valid': False,
                'message': 'Path is not a directory',
                'details': {'exists': True, 'is_directory': False}
            }

        # Check write permissions
        try:
            test_file = path_obj / '.chroma_write_test'
            test_file.touch()
            test_file.unlink()
            writable = True
        except Exception:
            writable = False

        if not writable:
            return {
                'valid': False,
                'message': 'Directory is not writable',
                'details': {'exists': True, 'is_directory': True, 'writable': False}
            }

        logger.debug(f"{log_prefix}Path validated: {path}")
        return {
            'valid': True,
            'message': 'Valid directory',
            'details': {'exists': True, 'is_directory': True, 'writable': True}
        }

    def test_connection(self, config_data, request_id=None):
        """Test ChromaDB connection with given configuration."""
        log_prefix = f"[{request_id}] " if request_id else ""
        mode = config_data.get('mode', 'local')

        try:
            if mode == 'local':
                path = config_data.get('local_path')
                if not path:
                    return {'success': False, 'message': 'Local path is required'}

                # Create directory if it doesn't exist
                Path(path).mkdir(parents=True, exist_ok=True)

                client = chromadb.PersistentClient(path=path)
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Local connection successful: {path}")
                return {
                    'success': True,
                    'message': f'Connected to local ChromaDB at {path}',
                    'collections': collection_names
                }

            elif mode == 'server':
                host = config_data.get('server_host', 'localhost')
                port = int(config_data.get('server_port', 8000))

                client = chromadb.HttpClient(host=host, port=port)
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Server connection successful: {host}:{port}")
                return {
                    'success': True,
                    'message': f'Connected to ChromaDB server at {host}:{port}',
                    'collections': collection_names
                }

            elif mode == 'cloud':
                tenant = config_data.get('cloud_tenant')
                database = config_data.get('cloud_database')
                api_key = Config.CHROMADB_API_KEY

                if not tenant:
                    return {'success': False, 'message': 'Tenant ID is required'}
                if not database:
                    return {'success': False, 'message': 'Database name is required'}
                if not api_key:
                    return {'success': False, 'message': 'CHROMADB_API_KEY not configured in .env'}

                client = chromadb.CloudClient(
                    tenant=tenant,
                    database=database,
                    api_key=api_key
                )
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Cloud connection successful: {tenant}/{database}")
                return {
                    'success': True,
                    'message': f'Connected to ChromaDB Cloud ({tenant}/{database})',
                    'collections': collection_names
                }

            else:
                return {'success': False, 'message': f'Unknown mode: {mode}'}

        except Exception as e:
            logger.error(f"{log_prefix}Connection test failed: {e}")
            return {'success': False, 'message': str(e)}

    def get_api_key_status(self, request_id=None):
        """Check if CHROMADB_API_KEY is configured in environment."""
        api_key = Config.CHROMADB_API_KEY

        if not api_key:
            return {'configured': False, 'masked': None}

        # Mask the key (show first 4 and last 4 chars)
        if len(api_key) > 8:
            masked = api_key[:4] + '...' + api_key[-4:]
        else:
            masked = '****'

        return {'configured': True, 'masked': masked}


# Singleton instance
rag_config_service = RagConfigService()
