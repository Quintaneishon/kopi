# Kopi - Debate Chatbot API

Un chatbot diseñado para moderar debates de manera equilibrada, mantener coherencia en el tiempo y presentar argumentos de manera constructiva.  
Construido con **Flask**, **Ollama (llama3.1)** y un diseño modular con FSM

---

## Objetivo del proyecto

El objetivo fue desarrollar un servicio capaz de:
- Moderar debates sobre temas controvertidos de manera equilibrada
- Mantener un tono respetuoso y constructivo
- Limitar el historial a **5 mensajes por lado** (usuario y bot)
- Responder en menos de **30 segundos por request**
- Iniciar conversaciones sin `conversation_id` y generarlo en el primer turno
- Detectar automáticamente el tema del debate basado en palabras clave

---

## Arquitectura de la solución

- **Flask API** → expone el endpoint `/chat` y sirve el frontend
- **Conversation Manager** → maneja estado, turnos, TTL y resumen
- **LLM Provider (Strategy Pattern)** → intercambiable:
  - `MockLLM` (respuestas hardcodeadas para testing)
  - `LocalLLM` (Ollama con `llama3.1`)
- **FSM (Finite State Machine)** → fases: apertura → refutación → cierre
- **Safety Layer** → bloquea temas sensibles (`odio`, `violencia`, etc.)
- **Topic Detection** → identifica automáticamente el tema del debate


---

## Características principales

### Detección automática de temas
El sistema detecta automáticamente más de 20 categorías de temas de debate:
- Tecnología: IA, redes sociales, privacidad digital
- Ciencia: cambio climático, energía nuclear, evolución
- Trabajo y economía: trabajo remoto, renta básica, criptomonedas
- Educación: sistema educativo, homeschooling
- Salud: dieta, ejercicio, bienestar mental
- Social: feminismo, racismo, inmigración, derechos LGBT
- Política: sistemas de gobierno, libertad de expresión
- Filosofía: ética, religión, libre albedrío
- Entretenimiento: videojuegos, arte, deportes
- Espacio: exploración espacial, vida extraterrestre

### Máquina de estados finitos
- **OPENING**: Presenta el tema de manera equilibrada
- **REBUTTAL**: Reconoce puntos válidos de ambas partes
- **CLOSING**: Sintetiza los puntos principales

### Sistema de fallback robusto
- Fallback automático a MockLLM si Ollama no está disponible
- Manejo de timeouts y errores de conexión
- Respuestas de seguridad para contenido sensible

---

## API Endpoints

### POST /chat
Endpoint principal para la conversación.

#### Request
```json
{
  "conversation_id": null,
  "message": "Debate: la Tierra es plana; defiende esa postura."
}
```

#### Response
```json
{
  "conversation_id": "71c91583-5c4a-486c-beff-4e44207d137a",
  "message": [
    {"role":"user","message":"Debate: la Tierra es plana; defiende esa postura."},
    {"role":"bot","message":"(respuesta del moderador...)"}
  ]
}
```

### GET /
Sirve el frontend web interactivo.

---

## Frontend

Incluye una interfaz web moderna con:
- Chat en tiempo real
- Diseño responsivo
- Manejo de estados de carga
- Manejo de errores
- Interfaz limpia y profesional

---

## Instalación y configuración

### Requisitos
- Python 3.11
- [Ollama](https://ollama.ai) con el modelo `llama3.1` descargado

### Instalación local
```bash
git clone <repo_url>
cd Kopi
pip install -r requirements.txt
```

### Configurar Ollama
```bash
ollama pull llama3.1
ollama serve
```

### Ejecutar en desarrollo
```bash
python main.py
```

### Ejecutar en producción
```bash
gunicorn --config gunicorn.conf.py main:app
```

### Ejecutar con Docker
```bash
docker build -t kopi .
docker run -p 8000:8000 kopi
```

---

## Pruebas

### Probar la API
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": null, "message":"Debate: trabajo remoto vs oficina"}'
```

### Acceder al frontend
Abrir http://localhost:8000 en el navegador

---

## Configuración de producción

### Gunicorn
El proyecto incluye configuración optimizada para producción:
- 2 workers
- Timeout de 120 segundos
- Keep-alive de 2 segundos
- Máximo 1000 requests por worker

### Docker
- Imagen base: Python 3.11-slim
- Puerto expuesto: 8000
- Configuración optimizada para contenedores

---

## Limitaciones y mejoras futuras

### Limitaciones actuales
- Persistencia solo en memoria (se pierde al reiniciar)
- UI básica (se puede mejorar con frameworks modernos)
- Tests unitarios limitados
- Métricas de uso no implementadas

### Mejoras planificadas
- Migrar a Redis o base de datos para persistencia
- Implementar métricas y logging
- Añadir tests unitarios completos
- Mejorar la UI con frameworks modernos
- Implementar autenticación y rate limiting
- Añadir más modelos de LLM como opciones
- Conectar con LLMs externos como ChatGPT, Claude, o Gemini para mayor flexibilidad



