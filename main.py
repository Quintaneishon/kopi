from flask import Flask, request, jsonify
from uuid import uuid4
from datetime import datetime, timedelta

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

llm: LLMProvider = MockLLM()

def next_policy_step(turn: int) -> str:
    if turn == 0: return "OPENING"
    if turn < 4:  return "REBUTTAL"
    return "CLOSING"

def build_prompt(state, history_last5):
    policy = next_policy_step(state["turn"])
    guide = {
      "OPENING": "Declara postura clara, 1 argumento fuerte, tono calmado, termina con 1 pregunta abierta.",
      "REBUTTAL": "Reconoce parte del punto, refuta con 1–2 razones o analogía, re-encuadra, termina con micro-pregunta.",
      "CLOSING": "Sintetiza acuerdos, fija criterio de decisión, sugiere prueba mental/falsable; cierra invitando a evaluar ese criterio."
    }[policy]

    system = (
      f"Rol: persuasivo, sereno, no hostil. Mantén el tema '{state['topic']}' y la postura '{state['stance']}'. "
      "No cambies de lado. 120–200 palabras. Párrafos cortos. 1 pregunta final. Evita divagar."
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
    if "tierra" in msg and "plana" in msg:
        return ("Forma de la Tierra", "La Tierra es plana")
    return ("Trabajo remoto vs oficina", "Pro trabajo remoto")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
