import os
import json
import requests
from pathlib import Path

TOKEN = os.environ['TG_BOT_TOKEN']
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

last_id_file = Path('last_update_id.txt')
last_update_id = 0
if last_id_file.exists():
    content = last_id_file.read_text().strip()
    if content.isdigit():
        last_update_id = int(content)

print(f"Начинаем с update_id: {last_update_id}")

response = requests.get(f"{BASE_URL}/getUpdates", params={
    'offset': last_update_id + 1,
    'limit': 100,
    'timeout': 0
})

data = response.json()
if not data.get('ok'):
    print(f"Ошибка Telegram API: {data}")
    exit(1)

updates = data['result']
print(f"Получено обновлений: {len(updates)}")

Path('images').mkdir(exist_ok=True)

# Загружаем существующие подписи
captions_file = Path('images/captions.json')
captions = {}
if captions_file.exists():
    try:
        captions = json.loads(captions_file.read_text(encoding='utf-8'))
    except Exception:
        captions = {}

new_last_id = last_update_id
saved_count = 0

for update in updates:
    update_id = update['update_id']
    if update_id > new_last_id:
        new_last_id = update_id

    msg = update.get('channel_post') or update.get('message')
    if not msg:
        continue

    msg_id = msg['message_id']
    file_id = None
    ext = None

    if msg.get('photo'):
        photo = sorted(msg['photo'], key=lambda p: p.get('file_size', 0), reverse=True)[0]
        file_id = photo['file_id']
        ext = 'jpg'
    elif msg.get('video'):
        file_id = msg['video']['file_id']
        ext = 'mp4'
    elif msg.get('video_note'):
        file_id = msg['video_note']['file_id']
        ext = 'mp4'

    if not file_id:
        continue

    filename = f"review_{msg_id}.{ext}"
    target = Path(f'images/{filename}')

    if target.exists():
        print(f"Уже существует: {target}")
        continue

    file_resp = requests.get(f"{BASE_URL}/getFile", params={'file_id': file_id})
    file_data = file_resp.json()

    if not file_data.get('ok'):
        print(f"Не удалось получить файл: {file_data}")
        continue

    file_path = file_data['result']['file_path']
    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    img_response = requests.get(download_url, timeout=60)
    if img_response.status_code == 200:
        target.write_bytes(img_response.content)
        print(f"Сохранено: {target} ({len(img_response.content)//1024} КБ)")
        saved_count += 1

        # Сохраняем подпись (текст под фото/видео), если есть
        caption = msg.get('caption', '').strip()
        if caption:
            captions[filename] = caption
    else:
        print(f"Ошибка загрузки: {img_response.status_code}")

# Сохраняем файл подписей
captions_file.write_text(json.dumps(captions, ensure_ascii=False, indent=2), encoding='utf-8')

last_id_file.write_text(str(new_last_id))
print(f"Готово. Новых файлов: {saved_count}. Последний ID: {new_last_id}")
