"""
Web Push — envia notificacoes push para subscricoes ativas do usuario.
Usa pywebpush com VAPID keys.
"""

import json

from loguru import logger
from pywebpush import WebPushException, webpush

from app.core.config import settings


def enviar_push(endpoint: str, chave_p256dh: str, chave_auth: str, payload: dict) -> bool:
    """
    Envia notificacao push para uma subscricao.
    Retorna True se enviou com sucesso, False se subscricao expirou (410).
    """
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {
                    "p256dh": chave_p256dh,
                    "auth": chave_auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={
                "sub": f"mailto:{settings.vapid_claims_email}",
            },
        )
        return True
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            # Subscricao revogada pelo browser — marcar como inativa
            logger.info("Subscricao push revogada (410): {}", endpoint[:50])
            return False
        logger.warning("Erro ao enviar push: {}", str(e))
        return True  # Erro temporario — nao desativar subscricao
    except Exception as e:
        logger.warning("Erro inesperado no push: {}", str(e))
        return True
