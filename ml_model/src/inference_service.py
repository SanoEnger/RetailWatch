import joblib
import pandas as pd
import numpy as np
from typing import List, Dict, Union
import logging


class InferenceService:
    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)
        self.logger = self._setup_logger()
    
    def _load_model(self, model_path: str):
        """Загрузить обученную модель"""
        try:
            model = joblib.load(model_path)
            return model
        except Exception as e:
            self.logger.error(f"Не удалось загрузить модель из {model_path}: {str(e)}")
            raise
    
    def _setup_logger(self):
        """Настроить логгер для службы инференса"""
        logger = logging.getLogger('InferenceService')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def predict(self, input_data: Union[List, Dict, pd.DataFrame]) -> List:
        """Выполнить предсказание на основе входных данных"""
        try:
            # Преобразовать ввод в подходящий формат
            processed_input = self._preprocess_input(input_data)
            
            # Выполнить предсказание
            predictions = self.model.predict(processed_input)
            
            # Зарегистрировать событие предсказания
            self.logger.info(f"Выполнено {len(predictions)} предсказаний")
            
            return predictions.tolist()
        except Exception as e:
            self.logger.error(f"Предсказание не выполнено: {str(e)}")
            raise
    
    def _preprocess_input(self, input_data: Union[List, Dict, pd.DataFrame]):
        """Предварительная обработка входных данных в соответствии с ожиданиями модели"""
        if isinstance(input_data, dict):
            input_data = [input_data]
        
        if isinstance(input_data, list):
            input_data = pd.DataFrame(input_data)
        
        return input_data
    
    def predict_proba(self, input_data: Union[List, Dict, pd.DataFrame]) -> List:
        """Получить вероятности предсказания"""
        try:
            processed_input = self._preprocess_input(input_data)
            
            # Проверить, поддерживает ли модель predict_proba
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(processed_input)
                return probabilities.tolist()
            else:
                raise AttributeError("Модель не поддерживает предсказания вероятностей")
        except Exception as e:
            self.logger.error(f"Предсказание вероятностей не выполнено: {str(e)}")
            raise