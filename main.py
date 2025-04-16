import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
        privacy_terms = ['privacy', 'privacy policy', 'политика конфиденциальности', 'конфиденциальность']
        
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

def main():
    try:
        # Подключаемся к Google Sheets
        client = setup_google_sheets()
        
        # Получаем список всех таблиц
        logger.info("Получаю список доступных таблиц...")
        spreadsheets = client.openall()
        
        if not spreadsheets:
            logger.error("Не найдено доступных таблиц. Проверьте права доступа.")
            return
            
        logger.info(f"Найдено {len(spreadsheets)} таблиц:")
        for i, sheet in enumerate(spreadsheets):
            logger.info(f"{i+1}. {sheet.title}")
            
        # Выбираем первую таблицу или просим пользователя выбрать
        if len(spreadsheets) == 1:
            sheet = spreadsheets[0].sheet1
            logger.info(f"Автоматически выбрана таблица: {sheet.spreadsheet.title}")
        else:
            choice = input("\nВыберите номер таблицы: ")
            sheet = spreadsheets[int(choice)-1].sheet1
            logger.info(f"Выбрана таблица: {sheet.spreadsheet.title}")
        
        # Получаем все URL из первого столбца
        logger.info("Читаю данные из первого столбца...")
        urls = sheet.col_values(1)
        if not urls:
            logger.error("Первый столбец пустой. Добавьте URL сайтов в столбец A.")
            return
        
        # Проверяем, есть ли заголовок
        if len(urls) < 2:
            logger.error("В таблице только заголовок. Добавьте URL сайтов в столбец A.")
            return
            
        # Пропускаем первый ряд (заголовок)
        urls = urls[1:]
        logger.info(f"Пропускаю заголовок: {urls[0]}")
        
        logger.info(f"Найдено {len(urls)} URL для обработки")
        
        # Создаем новый столбец для результатов
        results = []
        for i, url in enumerate(urls, 2):  # Начинаем с индекса 2 (второй ряд)
            if url:  # Проверяем, что URL не пустой
                logger.info(f"Обрабатываю ячейку A{i}: {url}")
                privacy_link = find_privacy_policy_link(url.strip())
                results.append([privacy_link])
                
                # Обновляем результаты в реальном времени
                logger.info(f"Записываю результат в ячейку B{i}: {privacy_link}")
                sheet.update(f'B{i}', [[privacy_link]])
        
        logger.info("Поиск успешно завершен!")
        
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main() 