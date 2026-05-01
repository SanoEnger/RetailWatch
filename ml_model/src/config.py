import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Управляет конфигурацией ML моделей"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из файла или вернуть значения по умолчанию"""
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif self.config_path.endswith('.json'):
                    return json.load(f)
        
        # Вернуть конфигурацию по умолчанию
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Вернуть значения конфигурации по умолчанию"""
        return {
            "model_type": "RandomForest",
            "model_params": {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            },
            "training_params": {
                "test_size": 0.2,
                "validation_split": 0.2
            },
            "data_params": {
                "feature_columns": [],
                "target_column": "target"
            }
        }
    
    def get_model_config(self) -> Dict[str, Any]:
        """Получить конфигурацию конкретной модели"""
        return self.config.get("model_params", {})
    
    def get_training_config(self) -> Dict[str, Any]:
        """Получить конфигурацию обучения"""
        return self.config.get("training_params", {})
    
    def get_data_config(self) -> Dict[str, Any]:
        """Получить конфигурацию обработки данных"""
        return self.config.get("data_params", {})
    
    def update_config(self, updates: Dict[str, Any]):
        """Обновить конфигурацию новыми значениями"""
        self.config.update(updates)