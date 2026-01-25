"""
Infisical Secrets Integration
Pulls secrets from Infisical at runtime.
Only INFISICAL_TOKEN needed in LangSmith Cloud environment variables.
"""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_secrets():
    """Load secrets from Infisical or fall back to environment variables."""
    
    infisical_token = os.getenv("INFISICAL_TOKEN")
    
    if infisical_token:
        try:
            from infisical_client import InfisicalClient, GetSecretOptions
            
            client = InfisicalClient(token=infisical_token)
            
            secrets = {}
            secret_names = [
                "ANTHROPIC_API_KEY",
                "GOOGLE_API_KEY", 
                "PERPLEXITY_API_KEY",
                "NCBI_API_KEY"
            ]
            
            for name in secret_names:
                try:
                    secret = client.get_secret(GetSecretOptions(
                        secret_name=name,
                        environment="prod"
                    ))
                    secrets[name] = secret.secret_value
                    os.environ[name] = secret.secret_value
                except Exception:
                    secrets[name] = os.getenv(name, "")
            
            return secrets
            
        except ImportError:
            pass
    
    return {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
        "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY", ""),
        "NCBI_API_KEY": os.getenv("NCBI_API_KEY", "")
    }


def get_secret(name: str) -> str:
    """Get a specific secret by name."""
    secrets = load_secrets()
    return secrets.get(name, os.getenv(name, ""))
