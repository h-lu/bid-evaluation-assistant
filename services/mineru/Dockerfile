# MinerU PDF Parser Service
# Based on official MinerU image with FastAPI wrapper

FROM opendatalab/mineru:latest

WORKDIR /app

# Install FastAPI and Uvicorn
RUN pip install --no-cache-dir fastapi uvicorn pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy service wrapper
COPY mineru_service.py /app/mineru_service.py

# Expose port
EXPOSE 8000

# Start service
CMD ["uvicorn", "mineru_service:app", "--host", "0.0.0.0", "--port", "8000"]
