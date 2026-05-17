"""
Тестовый скрипт для проверки работы API распознавания ценников
"""
import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """Проверка доступности API"""
    print("🔍 Проверка health endpoint...")
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        print("✅ API доступен")
        return True
    else:
        print(f"❌ API недоступен: {response.status_code}")
        return False

def test_recognize(image_path: str):
    """Тест распознавания изображения"""
    print(f"\n📸 Тест распознавания: {image_path}")
    
    if not Path(image_path).exists():
        print(f"❌ Файл не найден: {image_path}")
        return None
    
    with open(image_path, 'rb') as f:
        files = {'file': (Path(image_path).name, f, 'image/jpeg')}
        response = requests.post(f"{API_BASE_URL}/recognize", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Распознавание успешно!")
        print(f"   Цена: {data.get('price', 'N/A')}")
        print(f"   Название: {data.get('product_name', 'N/A')}")
        print(f"   Штрихкод: {data.get('barcode', 'N/A')}")
        print(f"   Вес: {data.get('weight', 'N/A')}")
        print(f"   Магазин: {data.get('store', 'N/A')}")
        print(f"   Уверенность: {data.get('confidence', 'N/A')}")
        print(f"   OCR текст: {data.get('raw_text', 'N/A')[:100]}...")
        return data
    else:
        print(f"❌ Ошибка распознавания: {response.status_code}")
        print(f"   {response.text}")
        return None

def test_export_csv():
    """Тест экспорта CSV"""
    print("\n📊 Тест экспорта CSV...")
    response = requests.get(f"{API_BASE_URL}/export/csv")
    
    if response.status_code == 200:
        filename = response.headers.get('Content-Disposition', '').split("filename*=")[-1]
        if filename:
            filename = filename.split("''")[-1]
            import urllib.parse
            filename = urllib.parse.unquote(filename)
        
        output_path = Path("test_export.csv")
        output_path.write_bytes(response.content)
        print(f"✅ CSV экспортирован: {output_path}")
        print(f"   Размер: {len(response.content)} байт")
        
        # Показать первые несколько строк
        content = response.content.decode('utf-8-sig')
        lines = content.split('\n')[:5]
        print("\n   Первые строки CSV:")
        for line in lines:
            print(f"   {line[:100]}")
        
        return True
    else:
        print(f"❌ Ошибка экспорта: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_history():
    """Тест получения истории"""
    print("\n📜 Тест получения истории...")
    response = requests.get(f"{API_BASE_URL}/history?limit=5&offset=0")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ История получена: {data['total']} записей")
        if data['items']:
            print(f"   Последняя запись:")
            item = data['items'][0]
            print(f"   - ID: {item['id'][:8]}...")
            print(f"   - Цена: {item.get('extracted_price', 'N/A')}")
            print(f"   - Название: {item.get('product_name', 'N/A')}")
            print(f"   - Штрихкод: {item.get('barcode', 'N/A')}")
            print(f"   - Вес: {item.get('weight', 'N/A')}")
            print(f"   - Магазин: {item.get('store', 'N/A')}")
        return True
    else:
        print(f"❌ Ошибка получения истории: {response.status_code}")
        return False

def main():
    print("=" * 60)
    print("🧪 Тестирование RetailWatch API")
    print("=" * 60)
    
    # Проверка health
    if not test_health():
        print("\n⚠️  API недоступен. Запустите backend сначала.")
        return
    
    # Тест истории (проверка что БД работает)
    test_history()
    
    # Тест экспорта CSV
    test_export_csv()
    
    # Если есть тестовые изображения, протестировать распознавание
    test_images = [
        "test_image.jpg",
        "test_pricetag.png",
    ]
    
    for image_path in test_images:
        if Path(image_path).exists():
            test_recognize(image_path)
        else:
            print(f"\n⚠️  Тестовое изображение не найдено: {image_path}")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)
    print("\n💡 Для полноценного теста:")
    print("   1. Поместите тестовое изображение ценника в корень проекта")
    print("   2. Назовите его test_image.jpg или test_pricetag.png")
    print("   3. Запустите скрипт снова")

if __name__ == "__main__":
    main()
