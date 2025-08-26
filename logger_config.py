"""
Advanced logging configuration for Fantacalcio-PY
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler


class StructuredLogger:
    """Structured logging with JSON support and Rich integration"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.console = Console()
        self._setup_logger()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        return {
            'level': 'INFO',
            'format': '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {message}',
            'file_output': False,
            'json_output': False,
            'log_file': 'logs/fantacalcio.log',
            'json_file': 'logs/fantacalcio.jsonl',
            'rotation': '10 MB',
            'retention': '1 week',
            'rich_handler': True
        }
    
    def _setup_logger(self):
        """Setup logger with configured handlers"""
        # Remove default handler
        logger.remove()
        
        # Console handler with Rich
        if self.config.get('rich_handler', True):
            logger.add(
                RichHandler(console=self.console, rich_tracebacks=True),
                level=self.config['level'],
                format="{message}",
                backtrace=True,
                diagnose=True
            )
        else:
            logger.add(
                sys.stderr,
                level=self.config['level'],
                format=self.config['format'],
                colorize=True,
                backtrace=True,
                diagnose=True
            )
        
        # File handler
        if self.config.get('file_output', False):
            log_file = Path(self.config['log_file'])
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                str(log_file),
                level=self.config['level'],
                format=self.config['format'],
                rotation=self.config.get('rotation', '10 MB'),
                retention=self.config.get('retention', '1 week'),
                backtrace=True,
                diagnose=True
            )
        
        # JSON handler for structured logging
        if self.config.get('json_output', False):
            json_file = Path(self.config['json_file'])
            json_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                str(json_file),
                level=self.config['level'],
                format="{message}",
                serialize=True,  # This enables JSON output
                rotation=self.config.get('rotation', '10 MB'),
                retention=self.config.get('retention', '1 week')
            )
    
    def bind_context(self, **kwargs) -> logger:
        """Bind context variables to logger"""
        return logger.bind(**kwargs)
    
    def log_operation_start(self, operation: str, **context):
        """Log the start of an operation with context"""
        logger.bind(
            operation=operation,
            status="started",
            timestamp=datetime.now().isoformat(),
            **context
        ).info(f"Starting {operation}")
    
    def log_operation_end(self, operation: str, success: bool = True, **context):
        """Log the end of an operation with context"""
        status = "completed" if success else "failed"
        level = "info" if success else "error"
        
        bound_logger = logger.bind(
            operation=operation,
            status=status,
            timestamp=datetime.now().isoformat(),
            **context
        )
        
        if level == "info":
            bound_logger.info(f"{operation.capitalize()} {status}")
        else:
            bound_logger.error(f"{operation.capitalize()} {status}")
    
    def log_data_summary(self, source: str, count: int, **metadata):
        """Log data processing summary"""
        logger.bind(
            source=source,
            record_count=count,
            data_type="player_data",
            timestamp=datetime.now().isoformat(),
            **metadata
        ).info(f"Processed {count} records from {source}")
    
    def log_analysis_metrics(self, metrics: Dict[str, Any]):
        """Log analysis metrics in structured format"""
        logger.bind(
            metrics=metrics,
            event_type="analysis_metrics",
            timestamp=datetime.now().isoformat()
        ).info("Analysis metrics calculated")
    
    def log_error_with_context(self, error: Exception, operation: str, **context):
        """Log error with full context"""
        logger.bind(
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            status="error",
            timestamp=datetime.now().isoformat(),
            **context
        ).error(f"Error in {operation}: {error}")


class PerformanceLogger:
    """Logger for performance monitoring"""
    
    def __init__(self, structured_logger: StructuredLogger):
        self.logger = structured_logger
        self._timers = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self._timers[operation] = datetime.now()
        self.logger.log_operation_start(operation)
    
    def end_timer(self, operation: str, success: bool = True, **context):
        """End timing an operation and log performance metrics"""
        if operation not in self._timers:
            logger.warning(f"No timer found for operation: {operation}")
            return
        
        start_time = self._timers.pop(operation)
        duration = (datetime.now() - start_time).total_seconds()
        
        performance_context = {
            "duration_seconds": round(duration, 3),
            "performance_category": self._get_performance_category(duration),
            **context
        }
        
        self.logger.log_operation_end(operation, success, **performance_context)
    
    def _get_performance_category(self, duration_seconds: float) -> str:
        """Categorize performance based on duration"""
        if duration_seconds < 1:
            return "fast"
        elif duration_seconds < 10:
            return "normal"
        elif duration_seconds < 60:
            return "slow"
        else:
            return "very_slow"


class DataQualityLogger:
    """Logger for data quality monitoring"""
    
    def __init__(self, structured_logger: StructuredLogger):
        self.logger = structured_logger
    
    def log_data_quality_check(self, source: str, checks: Dict[str, Any]):
        """Log data quality check results"""
        logger.bind(
            source=source,
            quality_checks=checks,
            event_type="data_quality",
            timestamp=datetime.now().isoformat()
        ).info(f"Data quality check for {source}")
    
    def log_missing_data(self, source: str, missing_fields: list, record_count: int):
        """Log missing data issues"""
        logger.bind(
            source=source,
            missing_fields=missing_fields,
            affected_records=record_count,
            severity="warning",
            event_type="data_quality_issue",
            timestamp=datetime.now().isoformat()
        ).warning(f"Missing data detected in {source}")
    
    def log_data_validation_error(self, source: str, field: str, invalid_count: int, total_count: int):
        """Log data validation errors"""
        error_rate = (invalid_count / total_count) * 100 if total_count > 0 else 0
        
        logger.bind(
            source=source,
            field=field,
            invalid_records=invalid_count,
            total_records=total_count,
            error_rate_percent=round(error_rate, 2),
            severity="error" if error_rate > 10 else "warning",
            event_type="validation_error",
            timestamp=datetime.now().isoformat()
        ).error(f"Validation error in {source}.{field}: {invalid_count}/{total_count} records")


# Global logger instances
_structured_logger: Optional[StructuredLogger] = None
_performance_logger: Optional[PerformanceLogger] = None
_data_quality_logger: Optional[DataQualityLogger] = None


def setup_logging(config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """Setup and configure global logging"""
    global _structured_logger, _performance_logger, _data_quality_logger
    
    _structured_logger = StructuredLogger(config)
    _performance_logger = PerformanceLogger(_structured_logger)
    _data_quality_logger = DataQualityLogger(_structured_logger)
    
    return _structured_logger


def get_logger() -> StructuredLogger:
    """Get global structured logger"""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = setup_logging()
    return _structured_logger


def get_performance_logger() -> PerformanceLogger:
    """Get global performance logger"""
    global _performance_logger
    if _performance_logger is None:
        setup_logging()
    return _performance_logger


def get_data_quality_logger() -> DataQualityLogger:
    """Get global data quality logger"""
    global _data_quality_logger
    if _data_quality_logger is None:
        setup_logging()
    return _data_quality_logger


# Convenience functions for common logging patterns
def log_step(step_name: str):
    """Decorator for logging function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            perf_logger = get_performance_logger()
            perf_logger.start_timer(step_name)
            
            try:
                result = func(*args, **kwargs)
                perf_logger.end_timer(step_name, success=True)
                return result
            except Exception as e:
                perf_logger.end_timer(step_name, success=False)
                get_logger().log_error_with_context(e, step_name)
                raise
        
        return wrapper
    return decorator