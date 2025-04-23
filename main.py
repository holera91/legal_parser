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
from url_processing import process_urls
from site_validation import validate_sites
from gemini_api import process_gemini_data

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
    logging.basicConfig(level=logging.INFO)
    
    # Завантажуємо конфігурацію
    config = load_config()
    spreadsheet_id = config['spreadsheet_id']
    sheet_name = config['sheet_name']
    data_range = config['range']
    
    client = setup_google_sheets()
    
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.worksheet(sheet_name)

    while True:
        print("Виберіть функцію:")
        print("1. Пошук URL Privacy Notes")
        print("2. Перевірка валідності сайтів")
        print("3. Передача даних до Gemini API")
        print("0. Вихід")

        choice = input("Ваш вибір: ")

        if choice == '1':
            process_urls(sheet, config)
        elif choice == '2':
            validate_sites(sheet, config)
        elif choice == '3':
            process_gemini_data(sheet, config)
        elif choice == '0':
            break
        else:
            print("Невірний вибір, спробуйте ще раз.")

if __name__ == "__main__":
    main() 