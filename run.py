import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Автоматическая перезагрузка при изменении кода
        workers=1,    # Количество воркеров
        log_level="info"  # Уровень логирования
    ) 