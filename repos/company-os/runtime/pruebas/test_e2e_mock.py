#!/usr/bin/env python3
"""Prueba punta a punta con un servidor mock (sin gastar ni un centavo).

Levanta un servidor HTTP que imita la API de OpenAI, apunta el runtime hacia él
y ejecuta un agente real (conciliador). Valida:
  1. El prompt del sistema se compone de ficha + SKILL.md.
  2. El HTTP sale con el formato correcto.
  3. La respuesta vuelve y se registra en la auditoría.

Uso:  python3 pruebas/test_e2e_mock.py
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

RESPUESTA_MOCK = "MOCK: conciliación de prueba completada sin diferencias."
RECIBIDO = {}


class MockOpenAI(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - nombre requerido por http.server
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        RECIBIDO.update(cuerpo)
        payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": RESPUESTA_MOCK},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silenciar el log del servidor
        pass


def main() -> int:
    servidor = HTTPServer(("127.0.0.1", 0), MockOpenAI)
    puerto = servidor.server_address[1]
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()

    os.environ["LITELLM_BASE_URL"] = f"http://127.0.0.1:{puerto}/v1"
    os.environ["LITELLM_MASTER_KEY"] = "test-key"

    # Aislar la auditoría de prueba
    import nucleo.auditoria as auditoria
    auditoria.ARCHIVO = "/tmp/auditoria_test_e2e.jsonl"
    if os.path.exists(auditoria.ARCHIVO):
        os.remove(auditoria.ARCHIVO)

    from nucleo import agente, cliente

    fallos = []

    # 1. Prompt del sistema = ficha + skill
    sistema = agente.prompt_sistema("conciliador")
    if "conciliador" not in sistema.lower():
        fallos.append("el prompt del sistema no menciona al conciliador")
    if len(sistema) < 2000:
        fallos.append(f"prompt sospechosamente corto ({len(sistema)} caracteres): ¿se cargó la SKILL?")

    # 2+3. Ejecución punta a punta
    c = cliente.crear_cliente()
    resultado = agente.ejecutar_agente("conciliador", "Tarea de prueba: conciliá nada.", c)
    if resultado["texto"] != RESPUESTA_MOCK:
        fallos.append("la respuesta no es la del mock")
    if RECIBIDO.get("model") != "empresa-base":
        fallos.append(f"modelo inesperado: {RECIBIDO.get('model')}")
    mensajes = RECIBIDO.get("messages", [])
    roles = [m.get("role") for m in mensajes]
    if roles != ["system", "user"]:
        fallos.append(f"mensajes mal formados: {roles}")
    if not os.path.exists(auditoria.ARCHIVO):
        fallos.append("no se escribió la auditoría")

    servidor.shutdown()

    if fallos:
        print("FALLÓ:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("OK: prueba punta a punta con mock superada "
          f"(prompt {len(sistema)} caracteres, auditoría en {auditoria.ARCHIVO})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
