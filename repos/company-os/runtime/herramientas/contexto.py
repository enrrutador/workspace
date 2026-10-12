"""Contexto de ejecución: quién ejecuta lo hace y dentro de qué límites.

El contexto se establece en el límite de la API (no viene del LLM), se propaga
automáticamente y es inmutable: ningún agente puede cambiar su tenant_id.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextoEjecucion:
    """Identidad completa de una ejecución de agente o herramienta."""

    tenant_id: str = "principal"
    user_id: str = "fabian"
    agent_id: str = ""
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_execution_id: str | None = None
    session_id: str | None = None

    def __post_init__(self):
        for campo in ("tenant_id", "user_id", "agent_id", "execution_id"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor:
                raise ValueError(f"ContextoEjecucion.{campo} debe ser un string no vacío")
        if ".." in self.tenant_id or "/" in self.tenant_id:
            raise ValueError("tenant_id inválido")

    def derivar(self, agent_id: str, **cambios) -> "ContextoEjecucion":
        """Crea el contexto hijo para una delegación.

        Hereda tenant_id, user_id, límites y sesión; registra el padre.
        El hijo NUNCA puede cambiar el tenant (se ignora si se intenta).
        """
        cambios.pop("tenant_id", None)  # el tenant no se negocia
        return ContextoEjecucion(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            agent_id=agent_id,
            parent_execution_id=self.execution_id,
            session_id=self.session_id,
            **cambios,
        )
