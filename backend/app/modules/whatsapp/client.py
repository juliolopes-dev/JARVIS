"""
Cliente HTTP para a Evolution API v2.

Documentacao: https://doc.evolution-api.com/v2

Modo 1 (Observador) usa apenas:
- fetch_connection_state — saber se a sessao esta ativa
- fetch_instance — dados do perfil conectado
- get_qrcode — QR para reconectar quando cair
- restart_instance — forcar reconexao

`send_text` esta implementado mas NAO e chamado em nenhum fluxo do Modo 1.
Existe pronto para o Modo 2 (Comandante) sem precisar refatorar nada.
"""

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class EvolutionAPIError(Exception):
    """Erro de comunicacao com a Evolution API."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class EvolutionClient:
    """Cliente assincrono para a Evolution API v2."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        instance_name: str | None = None,
        timeout: float = 15.0,
    ):
        self.base_url = (base_url or settings.evolution_api_url or "").rstrip("/")
        self.api_key = api_key or settings.evolution_api_key
        self.instance_name = instance_name or settings.evolution_instance_name
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        # apikey aqui e a chave da instancia (gerada na criacao)
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.base_url or not self.api_key:
            raise EvolutionAPIError(
                "Evolution API nao configurada (EVOLUTION_API_URL ou EVOLUTION_API_KEY ausente)"
            )

        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(method, url, headers=self._headers(), json=json)
        except httpx.RequestError as e:
            logger.warning("Falha de rede na Evolution API | path={} | erro={}", path, str(e))
            raise EvolutionAPIError(f"Falha de rede: {e}") from e

        if resp.status_code >= 400:
            corpo = resp.text[:300]
            logger.warning(
                "Evolution API retornou erro | path={} | status={} | corpo={}",
                path, resp.status_code, corpo,
            )
            raise EvolutionAPIError(
                f"Evolution {resp.status_code}: {corpo}", status_code=resp.status_code
            )

        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    # ─── Status da instancia ────────────────────────────────────────────────

    async def fetch_connection_state(self) -> dict[str, Any]:
        """GET /instance/connectionState/{instance} — retorna {instance: {state: 'open'|'close'|'connecting'}}"""
        return await self._request("GET", f"/instance/connectionState/{self.instance_name}")

    async def fetch_instance(self) -> dict[str, Any]:
        """GET /instance/fetchInstances?instanceName=X — dados completos da instancia."""
        return await self._request(
            "GET", f"/instance/fetchInstances?instanceName={self.instance_name}"
        )

    # ─── QR Code / reconexao ────────────────────────────────────────────────

    async def connect_instance(self) -> dict[str, Any]:
        """GET /instance/connect/{instance} — gera/retorna QR Code para conectar."""
        return await self._request("GET", f"/instance/connect/{self.instance_name}")

    async def restart_instance(self) -> dict[str, Any]:
        """PUT /instance/restart/{instance} — reinicia a sessao Baileys."""
        return await self._request("PUT", f"/instance/restart/{self.instance_name}")

    # ─── Envio de mensagem (NAO usado no Modo 1, pronto para Modo 2) ───────

    async def send_text(
        self,
        numero: str,
        texto: str,
        delay: int = 0,
    ) -> dict[str, Any]:
        """
        POST /message/sendText/{instance}

        ⚠️ Modo 1 (Observador) NAO chama esta funcao. Manter implementada
        apenas para o Modo 2 (Comandante) futuro.
        """
        payload = {
            "number": numero,
            "text": texto,
            "delay": delay,
            "linkPreview": True,
        }
        return await self._request(
            "POST", f"/message/sendText/{self.instance_name}", json=payload
        )


# Instancia compartilhada — leve e thread-safe (HTTPX cria conexao a cada request)
client = EvolutionClient()
