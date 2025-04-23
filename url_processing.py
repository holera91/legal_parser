import gspread
import logging
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def find_privacy_policy_link(url):
    try:
        # Додаємо протокол, якщо його немає
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        logger.info(f"Перевіряємо сайт: {url}")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Не вдалося отримати доступ до {url}: статус код {response.status_code}")
            return f"Не вдалося отримати доступ: статус код {response.status_code}"  # Повертаємо детальну помилку
        
        soup = BeautifulSoup(response.text, 'html.parser')
        privacy_links = []
        
        # Шукаємо посилання на політику конфіденційності
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.get_text().lower()
            if href and ('privacy' in text or 'policy' in text):
                full_url = urljoin(url, href)
                privacy_links.append(full_url)
                logger.info(f"Знайдено посилання на політику конфіденційності: {full_url}")
        
        if not privacy_links:
            return "Не знайдено посилання на політику конфіденційності"  # Повертаємо повідомлення, якщо не знайдено
        
        return privacy_links[0]  # Повертаємо перше знайдене посилання
    
    except Exception as e:
        logger.error(f"Помилка при обробці {url}: {str(e)}")
        return f"Помилка при обробці: {str(e)}"  # Повертаємо детальну помилку

def process_urls(sheet, config):
    url_column = config['url_column']
    legal_url_column = config['legal_url_column']  # Отримуємо назву колонки для запису результатів
    
    # Отримуємо всі дані з листа
    all_data = sheet.get_all_records()
    
    # Знаходимо індекс колонки для URL та legal_url_column
    url_column_index = None
    legal_column_index = None
    
    for index, key in enumerate(all_data[0].keys()):
        if key == url_column:
            url_column_index = index
        if key == legal_url_column:
            legal_column_index = index
    
    if url_column_index is None:
        logger.error(f"Колонка '{url_column}' не знайдена.")
        return
    if legal_column_index is None:
        logger.error(f"Колонка '{legal_url_column}' не знайдена.")
        return

    # Збираємо URL з колонки, починаючи з першого рядка
    urls = []
    for row in all_data:  # Не пропускаємо заголовок
        url = row[url_column]
        if url:  # Додаємо тільки непусті URL
            urls.append(url)

    logger.info(f"Найдено {len(urls)} URL для обработки")

    results = []
    for i, current_url in tqdm(enumerate(urls, 2), total=len(urls), desc="Обработка URL", unit="URL"):
        logger.info(f"Обрабатываю ячейку A{i}: {current_url}")
        privacy_link = find_privacy_policy_link(current_url)
        
        # Якщо не вдалося отримати посилання, записуємо повідомлення про помилку
        if privacy_link is None:
            privacy_link = "Не вдалося отримати доступ"  # Записуємо повідомлення про помилку
        
        results.append([privacy_link])
        
        # Знаходимо букву колонки для legal_url_column
        legal_column_letter = chr(65 + legal_column_index)  # 65 - ASCII код для 'A'
        
        # Записуємо результат у колонку legal_url_column
        sheet.update(values=[[privacy_link]], range_name=f'{legal_column_letter}{i}')  # Записуємо в колонку з назвою legal_url_column

    logger.info("Поиск успешно завершен!")
