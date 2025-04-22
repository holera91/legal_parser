import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
import logging
from tqdm import tqdm
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='log.txt',
    filemode='w'
)
logger = logging.getLogger(__name__)

def setup_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    try:
        logger.info("Начинаю авторизацию в Google Sheets...")
        with open('credentials.json', 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
        client = gspread.authorize(creds)
        logger.info("Авторизация успешно завершена")
        print("Авторизация успешно завершена")  # Виводимо в консоль
        return client
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}")
        raise

def find_privacy_policy_link(url):
    try:
        # Добавляем протокол, если его нет
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        logger.info(f"Проверяю сайт: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Получен неожиданный статус код: {response.status_code}")
            return f"Ошибка: Статус код {response.status_code}"
            
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск ссылок, содержащих "privacy policy" или похожие термины
        privacy_links = []
        privacy_terms = ['privacy', 'privacy policy', 'legal', 'legal policy']
        
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.get_text().lower().strip()
            
            if not href:
                continue
                
            if any(term in text for term in privacy_terms):
                full_url = urljoin(url, href)
                privacy_links.append(full_url)
                logger.info(f"Найдена ссылка на политику конфиденциальности: {full_url}")
        
        if privacy_links:
            return privacy_links[0]
        
        # Если не нашли по тексту ссылки, ищем по href
        for link in soup.find_all('a'):
            href = link.get('href', '').lower()
            if any(term in href for term in privacy_terms):
                full_url = urljoin(url, href)
                logger.info(f"Найдена ссылка в URL: {full_url}")
                return full_url
        
        logger.warning(f"Ссылка на политику конфиденциальности не найдена для {url}")
        return "Не найдено"
    
    except Exception as e:
        logger.error(f"Ошибка при обработке {url}: {str(e)}")
        return f"Ошибка: {str(e)}"

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    try:
        # Загружаем конфигурацию
        config = load_config()
        spreadsheet_id = config['spreadsheet_id']
        sheet_name = config['sheet_name']
        data_range = config['range']
        
        # Подключаемся к Google Sheets
        client = setup_google_sheets()
        
        # Открываем таблицу по ID
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet(sheet_name)
        
        # Получаем данные из указанного диапазона
        urls = sheet.get(data_range)
        
        # Проверяем, есть ли заголовок
        if len(urls) < 2:
            logger.error("В таблице только заголовок. Добавьте URL сайтов в столбец A.")
            return
            
        # Пропускаем первый ряд (заголовок)
        urls = urls[1:]
        logger.info(f"Обрабатываем таблицу: {sheet_name}, найдено {len(urls)} URL для обработки")
        print(f"Обрабатываем таблицу: {sheet_name}, найдено {len(urls)} URL для обработки")  # Виводимо в консоль
        
        # Создаем новый столбец для результатов
        results = []
        
        # Инициализируем прогресс-бар
        for i, url in tqdm(enumerate(urls, 2), total=len(urls), desc="Обработка URL", unit="URL"):
            if url:  # Перевіряємо, що URL не пустий
                current_url = url[0].strip()  # Отримуємо URL
                # Форматируем сообщение для консоли
                sys.stdout.write(f"\r{i}/{len(urls)}   Обрабатывается: {current_url}")  # Виводимо прогрес
                sys.stdout.flush()  # Очищаємо буфер виводу
                privacy_link = find_privacy_policy_link(current_url)  # Використовуємо url[0]
                results.append([privacy_link])
                
                # Оновлюємо результати в реальному часі
                logger.info(f"Записываю результат в ячейку B{i}: {privacy_link}")
                sheet.update(values=[[privacy_link]], range_name=f'B{i}')
        
        print()  # Додаємо новий рядок після завершення прогресу
        logger.info("Поиск успешно завершен!")
        
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main() 