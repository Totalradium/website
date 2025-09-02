import os
from pathlib import Path

def get_secret(secret_name, default=None):
    """
    Get secret from /etc/secrets/<filename> or app root, fallback to environment variable
    """
    # Try /etc/secrets/ first (deployment platform standard)
    secrets_path = Path(f'/etc/secrets/{secret_name}')
    if secrets_path.exists():
        return secrets_path.read_text().strip()
    
    # Try app root
    app_root_path = Path(__file__).parent / secret_name
    if app_root_path.exists():
        return app_root_path.read_text().strip()
    
    # Fallback to environment variable
    return os.getenv(secret_name, default)