from flask import Flask, request, jsonify, send_from_directory
from uuid import uuid4
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

CONV = {}

class LLMProvider:
    def generate(self, prompt: str, max_tokens: int = 512, timeout_s: int = 25) -> str:
        raise NotImplementedError

class MockLLM(LLMProvider):
    def generate(self, prompt, max_tokens=512, timeout_s=25):
        last_user = ""
        for line in reversed(prompt.splitlines()):
            if line.startswith("USER:"):
                last_user = line.split(":",1)[1].strip().lower()
                break
        if any(k in last_user for k in ["foto","satelit","nasa","espacio"]):
            return ("Entiendo que menciones fotos; cuestiono su interpretación y calibración. "
                    "Sigo en mi postura por observaciones a nivel del mar y horizontes constantes. "
                    "¿Qué medición directa aceptarías como concluyente?")
        if any(k in last_user for k in ["avion","vuelan","derech"]):
            return ("Que un avión 'vuele recto' no implica curvatura perceptible: sigue superficies isobáricas y rutas óptimas. "
                    "Mantengo mi postura. ¿Compararías desvíos en una ruta larga con y sin curvatura?")
        return ("Reconozco parte de tu punto, pero sostengo mi postura por consistencia en observaciones locales. "
                "¿Qué experimento aceptarías como decisivo?")

class LocalLLM(LLMProvider):
    def __init__(self, base="http://host.docker.internal:11434/api/chat", model="llama3.1:latest"):
        self.base = base
        self.model = model
    def generate(self, prompt, max_tokens=512, timeout_s=25):
        body = {
            "model": self.model, 
            "messages":[{"role":"user","content":prompt}], 
            "options":{"num_predict": max_tokens},
            "stream": False
        }
        try:
            print(f"Sending request to Ollama: {self.base}")
            print(f"Model: {self.model}")
            print(f"Prompt: {prompt[:100]}...")
            
            r = requests.post(self.base, json=body, timeout=timeout_s)
            print(f"Response status: {r.status_code}")
            print(f"Response text: {r.text[:500]}...")
            
            r.raise_for_status()
            
            data = r.json()
            print(f"Parsed JSON: {data}")
            
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                print(f"Unexpected Ollama response format: {data}")
                return MockLLM().generate(prompt, max_tokens, timeout_s)
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error to Ollama: {e}")
            print("Falling back to MockLLM")
            return MockLLM().generate(prompt, max_tokens, timeout_s)
        except requests.exceptions.Timeout as e:
            print(f"Timeout error: {e}")
            print("Falling back to MockLLM")
            return MockLLM().generate(prompt, max_tokens, timeout_s)
        except (ValueError, KeyError) as e:
            print(f"Failed to parse Ollama response, falling back to MockLLM: {e}")
            print(f"Response text: {r.text[:200]}...")
            return MockLLM().generate(prompt, max_tokens, timeout_s)


#llm: LLMProvider = MockLLM()
llm = LocalLLM()

def next_policy_step(turn: int) -> str:
    if turn == 0: return "OPENING"
    if turn < 4:  return "REBUTTAL"
    return "CLOSING"

def build_prompt(state, history_last5):
    policy = next_policy_step(state["turn"])
    guide = {
      "OPENING": "Presenta el tema de manera equilibrada, menciona diferentes perspectivas, tono respetuoso, termina con 1 pregunta abierta.",
      "REBUTTAL": "Reconoce puntos válidos de ambas partes, presenta evidencia de manera balanceada, termina con micro-pregunta.",
      "CLOSING": "Sintetiza los puntos principales de ambas perspectivas, sugiere criterios de evaluación, cierra invitando a reflexión."
    }[policy]

    system = (
      f"Eres un moderador de debate educado y respetuoso. El tema es '{state['topic']}'. "
      "Presenta argumentos de manera equilibrada, reconoce diferentes perspectivas, y mantén un tono constructivo. "
      "120–200 palabras. Párrafos cortos. 1 pregunta final. Evita divagar."
      f" Resumen hasta ahora: {state['summary'][-350:]}"
    )
    conv = "\n".join([f"{r.upper()}: {m}" for r,m in history_last5])
    return f"{system}\n\nInstrucciones del turno: {guide}\n\nHistorial:\n{conv}\n\nBOT:"

def update_summary(old_summary: str, new_bot_msg: str) -> str:
    new = new_bot_msg[:200]
    merged = (old_summary + " | " + new)[:350]
    return merged

def safety_check(topic: str, text: str) -> bool:
    blocked = {"autolesión","odio","violencia","instrucciones ilegales"}
    return not any(b in text.lower() for b in blocked)

def trim_last5(history):
    return history[-10:]  # 5 user + 5 bot como máximo

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    conv_id = data.get("conversation_id")
    user_msg = data.get("message","").strip()
    if not user_msg:
        return jsonify({"error":"message is required"}), 400

    if not conv_id:
        conv_id = str(uuid4())
        topic, stance = extract_topic_stance(user_msg)
        CONV[conv_id] = {
            "state": {"topic": topic, "stance": stance, "summary": "", "turn": 0},
            "history": [("user", user_msg)],
            "ttl": datetime.utcnow() + timedelta(hours=2)
        }
    else:
        if conv_id not in CONV:
            return jsonify({"error":"conversation not found"}), 404
        CONV[conv_id]["history"].append(("user", user_msg))

    st = CONV[conv_id]["state"]
    hist5 = trim_last5(CONV[conv_id]["history"])

    if not safety_check(st["topic"], user_msg):
        bot = "No puedo continuar por políticas de seguridad. Volvamos al marco original del tema, sin contenido riesgoso."
    else:
        prompt = build_prompt(st, hist5)
        bot = llm.generate(prompt, max_tokens=512, timeout_s=25)

    if not safety_check(st["topic"], bot):
        bot = "Mantengo mi postura, pero evitaré contenido sensible. ¿Qué evidencia considerarías decisiva?"

    CONV[conv_id]["history"].append(("bot", bot))
    st["summary"] = update_summary(st["summary"], bot)
    st["turn"] += 1
    CONV[conv_id]["ttl"] = datetime.utcnow() + timedelta(hours=2)

    last = trim_last5(CONV[conv_id]["history"])
    return jsonify({
        "conversation_id": conv_id,
        "message": [{"role": r, "message": m} for r,m in last]
    })

def extract_topic_stance(first_msg: str):
    msg = first_msg.lower()
    
    # Technology and AI topics
    if any(k in msg for k in ["inteligencia artificial", "ia", "ai", "chatgpt", "robot", "automatización"]):
        return ("Inteligencia Artificial", "Debate sobre el impacto de la IA en la sociedad")
    if any(k in msg for k in ["redes sociales", "facebook", "instagram", "twitter", "tiktok", "social media"]):
        return ("Redes Sociales", "Debate sobre el impacto de las redes sociales")
    if any(k in msg for k in ["privacy", "privacidad", "datos personales", "vigilancia"]):
        return ("Privacidad Digital", "Debate sobre privacidad y protección de datos")
    
    # Science and Environment
    if any(k in msg for k in ["cambio climático", "calentamiento global", "co2", "emisiones"]):
        return ("Cambio Climático", "Debate sobre el cambio climático y sus soluciones")
    if any(k in msg for k in ["energía nuclear", "nuclear", "reactor", "uranio"]):
        return ("Energía Nuclear", "Debate sobre la energía nuclear como alternativa energética")
    if any(k in msg for k in ["tierra", "plana"]):
        return ("Forma de la Tierra", "Debate sobre la forma de la Tierra")
    if any(k in msg for k in ["evolución", "darwin", "creacionismo", "diseño inteligente"]):
        return ("Evolución vs Creacionismo", "Debate sobre la evolución y el creacionismo")
    if any(k in msg for k in ["vacunas", "vacunación", "antivacunas", "inmunización"]):
        return ("Vacunas", "Debate sobre la efectividad y seguridad de las vacunas")
    
    # Work and Economy
    if any(k in msg for k in ["trabajo remoto", "teletrabajo", "oficina", "presencial", "home office"]):
        return ("Trabajo Remoto vs Oficina", "Debate sobre trabajo remoto vs presencial")
    if any(k in msg for k in ["renta básica", "ingreso universal", "ubi", "subsidio"]):
        return ("Renta Básica Universal", "Debate sobre la renta básica universal")
    if any(k in msg for k in ["crypto", "criptomonedas", "bitcoin", "blockchain", "nft"]):
        return ("Criptomonedas", "Debate sobre el futuro de las criptomonedas")
    if any(k in msg for k in ["capitalismo", "socialismo", "comunismo", "sistema económico"]):
        return ("Sistemas Económicos", "Debate sobre diferentes sistemas económicos")
    
    # Education
    if any(k in msg for k in ["educación", "universidad", "colegio", "escuela", "estudios"]):
        return ("Educación", "Debate sobre el sistema educativo y sus reformas")
    if any(k in msg for k in ["homeschooling", "educación en casa", "escuela en casa"]):
        return ("Homeschooling", "Debate sobre la educación en casa vs escuela tradicional")
    
    # Health and Lifestyle
    if any(k in msg for k in ["dieta", "vegano", "vegetariano", "carnívoro", "alimentación"]):
        return ("Dieta y Alimentación", "Debate sobre diferentes tipos de dieta y alimentación")
    if any(k in msg for k in ["ejercicio", "gimnasio", "fitness", "deporte", "actividad física"]):
        return ("Ejercicio y Fitness", "Debate sobre la importancia del ejercicio físico")
    if any(k in msg for k in ["meditación", "mindfulness", "yoga", "bienestar mental"]):
        return ("Bienestar Mental", "Debate sobre prácticas de bienestar mental")
    
    # Social Issues
    if any(k in msg for k in ["feminismo", "igualdad de género", "machismo", "patriarcado"]):
        return ("Feminismo e Igualdad de Género", "Debate sobre feminismo e igualdad de género")
    if any(k in msg for k in ["racismo", "discriminación", "privilegio", "diversidad"]):
        return ("Racismo y Discriminación", "Debate sobre racismo y discriminación")
    if any(k in msg for k in ["inmigración", "migración", "refugiados", "fronteras"]):
        return ("Inmigración", "Debate sobre políticas de inmigración")
    if any(k in msg for k in ["aborto", "pro-choice", "pro-vida", "interrupción del embarazo"]):
        return ("Aborto", "Debate sobre el derecho al aborto")
    if any(k in msg for k in ["matrimonio", "gay", "lgbt", "orientación sexual", "identidad de género"]):
        return ("Derechos LGBT", "Debate sobre derechos de la comunidad LGBT")
    
    # Politics and Governance
    if any(k in msg for k in ["democracia", "autoritarismo", "dictadura", "gobierno"]):
        return ("Sistemas de Gobierno", "Debate sobre diferentes sistemas de gobierno")
    if any(k in msg for k in ["libertad de expresión", "censura", "cancel culture", "cultura de la cancelación"]):
        return ("Libertad de Expresión", "Debate sobre libertad de expresión y censura")
    if any(k in msg for k in ["armas", "control de armas", "segunda enmienda", "violencia armada"]):
        return ("Control de Armas", "Debate sobre el control de armas")
    
    # Philosophy and Ethics
    if any(k in msg for k in ["moral", "ética", "valores", "principios"]):
        return ("Ética y Moral", "Debate sobre principios éticos y morales")
    if any(k in msg for k in ["religión", "ateísmo", "agnóstico", "fe", "dios"]):
        return ("Religión vs Ateísmo", "Debate sobre religión y ateísmo")
    if any(k in msg for k in ["libre albedrío", "determinismo", "destino", "causalidad"]):
        return ("Libre Albedrío", "Debate sobre libre albedrío vs determinismo")
    
    # Entertainment and Culture
    if any(k in msg for k in ["videojuegos", "gaming", "juegos", "esports"]):
        return ("Videojuegos", "Debate sobre el impacto de los videojuegos")
    if any(k in msg for k in ["música", "arte", "cultura", "entretenimiento"]):
        return ("Arte y Cultura", "Debate sobre el valor del arte y la cultura")
    if any(k in msg for k in ["deportes", "fútbol", "basketball", "competencia"]):
        return ("Deportes", "Debate sobre la importancia de los deportes")
    
    # Space and Exploration
    if any(k in msg for k in ["espacio", "nasa", "marte", "exploración espacial", "universo"]):
        return ("Exploración Espacial", "Debate sobre la exploración espacial")
    if any(k in msg for k in ["vida extraterrestre", "aliens", "ovni", "ufo"]):
        return ("Vida Extraterrestre", "Debate sobre la existencia de vida extraterrestre")
    
    # Default fallback
    return ("Trabajo Remoto vs Oficina", "Debate sobre trabajo remoto vs presencial")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)