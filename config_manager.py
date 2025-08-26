"""
Configuration management with YAML support for Fantacalcio-PY
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class ScrapingConfig:
    """Configuration for data scraping"""
    max_workers: int = 5
    request_timeout: int = 30
    retry_attempts: int = 3
    delay_between_requests: float = 1.0
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class AnalysisConfig:
    """Configuration for data analysis"""
    peso_fantamedia: float = 0.6
    peso_punteggio: float = 0.4
    prezzo_minimo: int = 1
    prezzo_massimo: int = 500
    convenienza_minima: float = 0.5
    anno_corrente: int = 2025
    fstats_anno: int = 2024


@dataclass
class OutputConfig:
    """Configuration for output formatting"""
    excel_format: str = "xlsx"
    include_charts: bool = False
    max_players_display: int = 50
    decimal_precision: int = 2


@dataclass
class LoggingConfig:
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    file_output: bool = False
    log_file: str = "logs/fantacalcio.log"


@dataclass
class AppConfig:
    """Main application configuration"""
    scraping: ScrapingConfig
    analysis: AnalysisConfig  
    output: OutputConfig
    logging: LoggingConfig
    
    # Paths
    data_dir: str = "data"
    output_dir: str = "data/output" 
    cache_dir: str = "data/cache"
    
    # API URLs (base64 decoded values from original config)
    fpedia_base_url: str = "https://www.fantacalciopedia.com"
    fstats_base_url: str = "https://api.app.fantagoat.it/api"


class ConfigManager:
    """Manages application configuration with YAML support"""
    
    DEFAULT_CONFIG_FILE = "fantacalcio.yaml"
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from YAML file or create default"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                logger.debug(f"Loaded configuration from {config_path}")
                return self._dict_to_config(data)
            except Exception as e:
                logger.warning(f"Error loading config from {config_path}: {e}")
                logger.info("Using default configuration")
        
        # Return default configuration
        return self._get_default_config()
    
    def _get_default_config(self) -> AppConfig:
        """Get default configuration"""
        return AppConfig(
            scraping=ScrapingConfig(),
            analysis=AnalysisConfig(), 
            output=OutputConfig(),
            logging=LoggingConfig()
        )
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to AppConfig object"""
        return AppConfig(
            scraping=ScrapingConfig(**data.get('scraping', {})),
            analysis=AnalysisConfig(**data.get('analysis', {})),
            output=OutputConfig(**data.get('output', {})), 
            logging=LoggingConfig(**data.get('logging', {})),
            data_dir=data.get('data_dir', 'data'),
            output_dir=data.get('output_dir', 'data/output'),
            cache_dir=data.get('cache_dir', 'data/cache'),
            fpedia_base_url=data.get('fpedia_base_url', 'https://www.fantacalciopedia.com'),
            fstats_base_url=data.get('fstats_base_url', 'https://api.app.fantagoat.it/api')
        )
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save current configuration to YAML file"""
        file_path = config_file or self.config_file
        
        # Convert config to dict
        config_dict = {
            'scraping': asdict(self.config.scraping),
            'analysis': asdict(self.config.analysis),
            'output': asdict(self.config.output),
            'logging': asdict(self.config.logging),
            'data_dir': self.config.data_dir,
            'output_dir': self.config.output_dir,
            'cache_dir': self.config.cache_dir,
            'fpedia_base_url': self.config.fpedia_base_url,
            'fstats_base_url': self.config.fstats_base_url
        }
        
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2, sort_keys=True)
            
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def create_default_config_file(self) -> None:
        """Create a default configuration file"""
        if not Path(self.config_file).exists():
            self.save_config()
            logger.info(f"Created default configuration file: {self.config_file}")
        else:
            logger.info(f"Configuration file already exists: {self.config_file}")
    
    def get_file_paths(self) -> Dict[str, str]:
        """Get all file paths based on current configuration"""
        return {
            'giocatori_csv': os.path.join(self.config.data_dir, '_giocatori.csv'),
            'players_csv': os.path.join(self.config.data_dir, '_players.csv'),
            'giocatori_urls': os.path.join(self.config.data_dir, 'giocatori_urls.txt'),
            'fpedia_output': os.path.join(self.config.output_dir, 'fpedia_analysis.xlsx'),
            'fstats_output': os.path.join(self.config.output_dir, 'FSTATS_analysis.xlsx'),
            'cache_dir': self.config.cache_dir
        }
    
    def get_urls(self) -> Dict[str, str]:
        """Get all URLs based on current configuration"""
        return {
            'fpedia_lista': f"{self.config.fpedia_base_url}/lista-calciatori-serie-a/",
            'fstats_login': f"{self.config.fstats_base_url}/account/login/",
            'fstats_players': f"{self.config.fstats_base_url}/v1/zona/player/?page_size=1000&page=1&season={self.config.analysis.fstats_anno}%2F{str(self.config.analysis.fstats_anno+1)[-2:]}&ordering="
        }
    
    def update_config(self, section: str, **kwargs) -> None:
        """Update specific configuration section"""
        if hasattr(self.config, section):
            section_obj = getattr(self.config, section)
            for key, value in kwargs.items():
                if hasattr(section_obj, key):
                    setattr(section_obj, key, value)
                    logger.debug(f"Updated {section}.{key} = {value}")
                else:
                    logger.warning(f"Unknown configuration key: {section}.{key}")
        else:
            logger.warning(f"Unknown configuration section: {section}")


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None or config_file:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> AppConfig:
    """Get current application configuration"""
    return get_config_manager().config


# Backward compatibility functions for existing code
def get_file_paths() -> Dict[str, str]:
    """Get file paths for backward compatibility"""
    return get_config_manager().get_file_paths()


def get_urls() -> Dict[str, str]:
    """Get URLs for backward compatibility"""
    return get_config_manager().get_urls()