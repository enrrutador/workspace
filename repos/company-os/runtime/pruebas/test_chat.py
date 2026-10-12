#!/usr/bin/env python3
"""Prueba del chat multi-turno: el historial viaja en los mensajes al proveedor.

Mock del cliente OpenAI que captura `messages`; se verifica el orden
system -> user -> assistant -> user(tarea actual).
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

from nucleo import agente as modulo_agente  # noqa: E402


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self):
        self.message = _Msg("respuesta mock")


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


class _Resp:
    def __init__(self, capturado):
        self.choices = [_Choice()]
        self.usage = _Usage()
        self._capturado = capturado


class _Completions:
    def __init__(self, capturado):
        self._capturado = capturado

    def create(self, model, messages, temperature):
        self._capturado.extend(messages)
        return _Resp(self._capturado)


class _Chat:
    def __init__(self, capturado):
        self.completions = _Completions(capturado)


class MockCliente:
    def __init__(self, capturado):
        self.chat = _Chat(capturado)


def main() -> int:
    capturado = []
    historial = [
        {"rol": "usuario", "texto": "¿qué ideas hay esta semana?"},
        {"rol": "agente", "texto": "Tres tesis con evidencia."},
    ]
    # Sin depender de auditoría en disco: se usa igual, es append-only local.
    r = modulo_agente.ejecutar_agente(
        "explorador", "Contame la segunda con más detalle",
        MockCliente(capturado), historial=historial)
    assert r["texto"] == "respuesta mock", r
    roles = [m["role"] for m in capturado]
    assert roles == ["system", "user", "assistant", "user"], roles
    assert "Tres tesis" in capturado[2]["content"]
    assert capturado[3]["content"] == "Contame la segunda con más detalle"
    assert "Explorador" in capturado[0]["content"]  # ficha correcta

    # Sin historial: system + user, como antes.
    capturado2 = []
    modulo_agente.ejecutar_agente("explorador", "hola", MockCliente(capturado2))
    assert [m["role"] for m in capturado2] == ["system", "user"]

    # Historial inválido: falla rápido (el dashboard ya lo sanea antes).
    capturado3 = []
    try:
        modulo_agente.ejecutar_agente("explorador", "hola", MockCliente(capturado3),
                                     historial="no-es-lista")
        raise AssertionError("debió fallar con historial no-lista")
    except ValueError:
        pass

    print("OK: chat multi-turno (historial en mensajes + validación)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
