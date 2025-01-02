# Используем официальный образ Python
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы приложения
COPY . .

# Открываем порт, если требуется
EXPOSE 8080

# Команда для запуска
CMD ["python", "TransactionListener.py"]
