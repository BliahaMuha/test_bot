FROM python:3.11-alpine

# Установка зависимостей
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    libssl-dev \
#    libffi-dev \
#    python3-dev \
#    && rm -rf /var/lib/apt/lists/*

# Создание директории приложения
WORKDIR /code
COPY . /code/

# Копирование зависимостей в контейнер
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск бота
CMD ["python", "main.py"]