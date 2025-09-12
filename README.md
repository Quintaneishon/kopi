# Kopi Chat - API de Debate con Flask

Una API de Flask que simula un moderador de debate usando LLM local (Ollama) con fallback a MockLLM.

## Características

- API REST con Flask
- Integración con Ollama (LLM local)
- Fallback a MockLLM si Ollama no está disponible
- Frontend HTML minimalista
- Deploy con Gunicorn
- Containerización con Docker


## Instalación y Uso

### Opción 1: Ejecución Local con Gunicorn

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Ejecutar con Gunicorn:
```bash
chmod +x run_production.sh
./run_production.sh
```

O manualmente:
```bash
gunicorn -w 2 -b 0.0.0.0:8000 main:app
```

3. Abrir el navegador en `http://localhost:8000` y ver el archivo `index.html`

### Opción 2: Con Docker

1. Construir y ejecutar con Docker:
```bash
chmod +x run_docker.sh
./run_docker.sh
```

O manualmente:
```bash
docker build -t kopi-chat .
docker run -p 8000:8000 kopi-chat
```

2. Abrir el navegador en `http://localhost:8000` y ver el archivo `index.html`

## API Endpoints

### POST /chat

Envía un mensaje al chat de debate.

**Request:**
```json
{
    "conversation_id": "uuid-optional",
    "message": "Tu mensaje aquí"
}
```

**Response:**
```json
{
    "conversation_id": "uuid",
    "message": [
        {"role": "user", "message": "Mensaje del usuario"},
        {"role": "bot", "message": "Respuesta del bot"}
    ]
}
```

## Configuración

- **Puerto:** 8000
- **Workers:** 2 (Gunicorn)
- **Host:** 0.0.0.0 (acepta conexiones externas)
- **LLM:** Ollama (http://127.0.0.1:11434) con fallback a MockLLM

## Frontend

El frontend es una página HTML simple que:
- Muestra el historial de conversación
- Permite enviar mensajes
- Hace fetch a la API `/chat`
- Maneja errores y estados de carga

## Notas

- La aplicación usa Ollama como LLM principal
- Si Ollama no está disponible, usa MockLLM
- Las conversaciones tienen TTL de 2 horas
- Incluye verificación de seguridad básica