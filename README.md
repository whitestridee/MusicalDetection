# Поиск похожих музыкальных композиций

Учебный сервис на Python для поиска похожих аудиофайлов по содержимому сигнала.

## Что умеет проект

- строит индекс по базе `.wav` файлов;
- извлекает фиксированный вектор признаков из каждого трека;
- ищет наиболее похожие записи по косинусной близости;
- поддерживает три backend-а индексации: `numpy`, `faiss`, `hnsw`;
- возвращает `Top-N` результатов через CLI или HTTP-сервис.

## Структура

- `audio_similarity/audio.py` - загрузка и базовая нормализация WAV;
- `audio_similarity/features.py` - извлечение акустических признаков;
- `audio_similarity/index.py` - построение и загрузка индекса;
- `audio_similarity/search.py` - поиск похожих треков;
- `build_index.py` - индексация базы;
- `search_cli.py` - поиск из командной строки;
- `server.py` - простой HTTP API;
- `mvc_app/` - MVC-слой для веб-интерфейса;
- `generate_demo_dataset.py` - генерация тестового набора синтетических WAV.

## Алгоритм

Для каждого аудиофайла:

1. Сигнал переводится в моно и приводится к частоте дискретизации 16 кГц.
2. Аудио разбивается на перекрывающиеся окна.
3. Для каждого окна считаются признаки:
   - RMS-энергия;
   - zero-crossing rate;
   - спектральный центроид;
   - спектральная ширина;
   - спектральный rolloff;
   - spectral flatness;
   - сжатый лог-спектр;
   - mel-энергии;
   - MFCC и delta-MFCC.
4. По окнам вычисляются средние и стандартные отклонения, формируя единый embedding трека.
5. Перед поиском embeddings стандартизуются по статистикам базы и нормализуются.
6. Поиск выполняется через косинусную близость между embedding запроса и embedding базы.

## Быстрый старт

### 1. Подготовить базу треков

Положите `.wav` файлы в папку `dataset/`.

### 2. Создать локальное окружение

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r .\requirements.txt
```

Если нужен поиск через FAISS/HNSW:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install faiss-cpu hnswlib
```

### 3. Построить индекс

Baseline `numpy`:

```powershell
& ".\.venv\Scripts\python.exe" .\build_index.py --dataset .\dataset --output .\index_data --engine numpy
```

FAISS:

```powershell
& ".\.venv\Scripts\python.exe" .\build_index.py --dataset .\dataset --output .\index_data --engine faiss
```

HNSW:

```powershell
& ".\.venv\Scripts\python.exe" .\build_index.py --dataset .\dataset --output .\index_data_hnsw --engine hnsw --hnsw-m 16 --hnsw-ef-construction 200 --hnsw-ef-search 50
```

### 4. Выполнить поиск

```powershell
& ".\.venv\Scripts\python.exe" .\search_cli.py --query .\dataset\example.wav --index .\index_data --top-k 5 --engine auto
```

### 5. Запустить HTTP-сервис

```powershell
& ".\.venv\Scripts\python.exe" .\server.py --index .\index_data --host 127.0.0.1 --port 8000
```

Запрос через API:

```text
http://127.0.0.1:8000/search?query=C:/full/path/to/example.wav&top_k=5&engine=auto
```

## Демо без реальных треков

```powershell
& ".\.venv\Scripts\python.exe" .\generate_demo_dataset.py
& ".\.venv\Scripts\python.exe" .\build_index.py --dataset .\demo_dataset --output .\index_data --engine faiss
& ".\.venv\Scripts\python.exe" .\search_cli.py --query .\demo_dataset\tone_220.wav --index .\index_data --top-k 3 --engine auto
```


## Как улучшить проект

- заменить handcrafted-признаки на `PANNs`, `VGGish`, `CLAP` или другие pretrained audio embeddings;
- использовать более сложные варианты FAISS/HNSW;
- добавить сегментный поиск по нескольким окнам;
- расширить веб-интерфейс и добавить историю запросов.
