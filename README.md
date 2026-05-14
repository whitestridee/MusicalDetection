# Поиск похожих музыкальных композиций

Учебный сервис на Python для поиска похожих аудиофайлов по содержимому сигнала.

## Что умеет проект

- строит индекс по базе `.wav` файлов;
- извлекает фиксированный вектор признаков из каждого трека;
- ищет наиболее похожие записи по косинусной близости;
- возвращает `Top-N` результатов через CLI или HTTP-сервис.

## Структура

- `audio_similarity/audio.py` - загрузка и базовая нормализация WAV;
- `audio_similarity/features.py` - извлечение акустических признаков;
- `audio_similarity/index.py` - построение и загрузка индекса;
- `audio_similarity/search.py` - поиск похожих треков;
- `build_index.py` - индексация базы;
- `search_cli.py` - поиск из командной строки;
- `server.py` - простой HTTP API;
- `generate_demo_dataset.py` - генерация тестового набора синтетических WAV.

## Алгоритм

Для каждого аудиофайла:

1. сигнал переводится в моно и приводится к частоте дискретизации 16 кГц;
2. аудио разбивается на перекрывающиеся окна;
3. для каждого окна считаются признаки:
   - RMS-энергия;
   - zero-crossing rate;
   - спектральный центроид;
   - спектральная ширина;
   - спектральный rolloff;
   - spectral flatness;
   - сжатый лог-спектр.
4. затем по окнам берутся средние и стандартные отклонения, формируя единый embedding трека;
5. поиск выполняется через косинусную близость между embedding запроса и embedding базы.

Это не state-of-the-art, но для лабораторной работы это хороший и понятный baseline без сложных зависимостей.

## Быстрый старт

### 1. Подготовить базу треков

Положите `.wav` файлы в любую папку, например `dataset/`.

### 2. Построить индекс

```powershell
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\build_index.py --dataset .\dataset --output .\index_data
```

### 3. Выполнить поиск

```powershell
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\search_cli.py --query .\dataset\example.wav --index .\index_data --top-k 5
```

### 4. Запустить HTTP-сервис

```powershell
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\server.py --index .\index_data --host 127.0.0.1 --port 8000
```

Запрос:

```text
http://127.0.0.1:8000/search?query=C:/full/path/to/example.wav&top_k=5
```

## Демо без реальных треков

```powershell
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\generate_demo_dataset.py
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\build_index.py --dataset .\demo_dataset --output .\index_data
& "C:\Users\boris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\search_cli.py --query .\demo_dataset\tone_220.wav --index .\index_data --top-k 3
```

## Ограничения

- текущая версия поддерживает только PCM `.wav`;
- `.mp3` можно добавить позже через `librosa` или `ffmpeg`;
- индекс сейчас точный и полный, без FAISS/HNSW, что нормально для небольшой учебной базы.

