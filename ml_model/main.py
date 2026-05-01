import argparse
import sys
from pathlib import Path

# Добавить src в путь для импорта
sys.path.append(str(Path(__file__).parent / "src"))

from src.training_pipeline import ModelTrainer
from src.config import ConfigManager


def main():
    parser = argparse.ArgumentParser(description="Модуль ML RetailWatch")
    parser.add_argument("--mode", choices=["train", "infer"], required=True,
                        help="Режим работы: обучение или инференс")
    parser.add_argument("--config", type=str, help="Путь к файлу конфигурации")
    parser.add_argument("--data-path", type=str, help="Путь к входным данным")
    parser.add_argument("--model-path", type=str, help="Путь для сохранения/загрузки модели")
    
    args = parser.parse_args()
    
    config_manager = ConfigManager(args.config)
    
    if args.mode == "train":
        if not args.data_path:
            raise ValueError("--data-path обязателен для режима обучения")
        if not args.model_path:
            raise ValueError("--model-path обязателен для режима обучения")
        
        trainer = ModelTrainer(args.config)
        # Загрузить и обучить на данных
        # trainer.train_from_path(args.data_path)
        print(f"Обучение завершено. Модель сохранена в {args.model_path}")
        
    elif args.mode == "infer":
        if not args.model_path:
            raise ValueError("--model-path обязателен для режима инференса")
        if not args.data_path:
            raise ValueError("--data-path обязателен для режима инференса")
        
        # Инициализировать службу инференса и выполнить предсказания
        # service = InferenceService(args.model_path)
        # results = service.predict_from_path(args.data_path)
        print(f"Инференс завершен. Результаты получены из {args.model_path}")


if __name__ == "__main__":
    main()