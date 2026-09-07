FROM python:3.11-slim

# Crear usuario estándar para Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Instalar dependencias
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Copiar archivos de la aplicación
COPY --chown=user . /app

# Configuración de red para Hugging Face Spaces
ENV PORT=7860
ENV HOST=0.0.0.0
EXPOSE 7860

CMD ["python", "run.py"]
