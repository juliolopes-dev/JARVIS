"""
Teste comparativo: GPT-4o vs DeepSeek v4-pro nos 4 parsers NLP do Jarvis.

Uso:
    cd backend
    uv run python scripts/teste_parsers_deepseek.py

Requer no .env:
    OPENAI_API_KEY=...
    DEEPSEEK_API_KEY=...
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path

# Força UTF-8 no stdout do Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Adiciona o backend ao path para importar os prompts reais
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import AsyncOpenAI

# ── Clientes ────────────────────────────────────────────────────────────────

openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

deepseek_client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

AGORA = "2026-05-03T10:00:00-03:00 (sabado)"

# ── Prompts reais (importados do projeto) ───────────────────────────────────

from app.modules.ia.prompts import (
    LEMBRETE_PARSE_PROMPT,
    TAREFA_PARSE_PROMPT,
    TAREFA_RECORRENTE_PARSE_PROMPT,
    EVENTO_PARSE_PROMPT,
)

# ── Casos de teste ───────────────────────────────────────────────────────────
# Formato: (mensagem, parser, resultado_esperado_dict_parcial)
# resultado_esperado usa a chave booleana principal de cada parser

CASOS = [
    # ── LEMBRETE (pontual com horário) ──────────────────────────────────────
    ("me lembra amanha as 9h da reuniao com o fornecedor",
     "lembrete", {"eh_lembrete": True}),

    ("tenho consulta medica sexta as 14h",
     "lembrete", {"eh_lembrete": True}),

    ("amanha tenho reuniao com o pessoal da ATS as 9h30",
     "lembrete", {"eh_lembrete": True}),

    ("a reuniao da diretoria vai acontecer dia 10/06/2026",
     "lembrete", {"eh_lembrete": True}),

    # armadilha: recorrente, nao lembrete
    ("todo dia as 8h me manda o resumo do dia",
     "lembrete", {"eh_lembrete": False}),

    # armadilha: sem horário definido
    ("amanha tenho que ligar pro banco",
     "lembrete", {"eh_lembrete": False}),

    # armadilha: tarefa, nao lembrete
    ("adiciona ligar pro banco na minha lista de tarefas",
     "lembrete", {"eh_lembrete": False}),

    # ── TAREFA (checklist) ──────────────────────────────────────────────────
    ("adiciona comprar leite na lista Compras",
     "tarefa", {"eh_tarefa": True}),

    ("cria uma tarefa de ligar pro banco urgente",
     "tarefa", {"eh_tarefa": True}),

    ("coloca academia no checklist de saude",
     "tarefa", {"eh_tarefa": True}),

    # armadilha: lembrete, nao tarefa
    ("me lembra amanha as 9h da consulta",
     "tarefa", {"eh_tarefa": False}),

    # armadilha: conversa, nao tarefa
    ("qual e o horario de funcionamento da loja?",
     "tarefa", {"eh_tarefa": False}),

    # ── RECORRENTE (cron) ───────────────────────────────────────────────────
    ("todo dia as 7h me manda o briefing do dia",
     "recorrente", {"eh_recorrente": True}),

    ("toda segunda feira as 9h me lembra da reuniao de equipe",
     "recorrente", {"eh_recorrente": True}),

    ("dia 5 de todo mes me lembra de pagar o aluguel",
     "recorrente", {"eh_recorrente": True}),

    # armadilha classica: menciona regularidade MAS tem data unica
    ("a reuniao mensal da diretoria, realizada todo primeiro sabado, ocorrera em 10/05/2026",
     "recorrente", {"eh_recorrente": False}),

    # armadilha: pontual com hora, nao recorrente
    ("me lembra amanha as 9h da reuniao",
     "recorrente", {"eh_recorrente": False}),

    # ── EVENTO (memoria episodica) ──────────────────────────────────────────
    ("hoje visitei a loja de Salgueiro e resolvi o problema de estoque",
     "evento", {"eh_evento": True}),

    ("acabei de chegar de Petrolina, ficou tudo acertado com o gerente",
     "evento", {"eh_evento": True}),

    # armadilha: fato atemporal
    ("gosto muito de trabalhar com logistica",
     "evento", {"eh_evento": False}),

    # armadilha: tarefa, nao evento
    ("adiciona revisao do estoque de Juazeiro na lista",
     "evento", {"eh_evento": False}),
]

# ── Chamada ao modelo ────────────────────────────────────────────────────────

def extrair_json(texto: str) -> dict:
    """Extrai JSON de resposta que pode vir com markdown ou texto extra."""
    if not texto:
        raise ValueError("resposta vazia")
    texto = texto.strip()
    # Remove bloco ```json ... ```
    if "```" in texto:
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
        if match:
            texto = match.group(1)
    # Localiza primeiro { e último }
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio != -1 and fim != -1:
        texto = texto[inicio:fim + 1]
    return json.loads(texto)


async def chamar_parser(cliente: AsyncOpenAI, modelo: str, parser: str, mensagem: str) -> dict:
    prompt_map = {
        "lembrete": LEMBRETE_PARSE_PROMPT,
        "tarefa": TAREFA_PARSE_PROMPT,
        "recorrente": TAREFA_RECORRENTE_PARSE_PROMPT,
        "evento": EVENTO_PARSE_PROMPT,
    }
    prompt = prompt_map[parser].format(agora=AGORA, mensagem=mensagem)

    kwargs = dict(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500,
    )

    # DeepSeek v4-pro: desativa thinking para parsers (classificação simples)
    # thinking mode é incompatível com json_object response_format
    if "deepseek" in modelo:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    else:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = await cliente.chat.completions.create(**kwargs)
        return extrair_json(resp.choices[0].message.content or "")
    except Exception as e:
        return {"erro": str(e)}


# ── Execução dos testes ──────────────────────────────────────────────────────

async def rodar_caso(mensagem: str, parser: str, esperado: dict):
    gpt_task = chamar_parser(openai_client, "gpt-4o", parser, mensagem)
    ds_task = chamar_parser(deepseek_client, "deepseek-v4-pro", parser, mensagem)

    gpt_result, ds_result = await asyncio.gather(gpt_task, ds_task)
    return gpt_result, ds_result


def checar(resultado: dict, esperado: dict) -> bool:
    chave = list(esperado.keys())[0]
    return resultado.get(chave) == esperado[chave]


VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
NEGRITO = "\033[1m"
RESET = "\033[0m"
CINZA = "\033[90m"


async def main():
    print(f"\n{NEGRITO}{'='*70}{RESET}")
    print(f"{NEGRITO}  TESTE COMPARATIVO — GPT-4o vs DeepSeek v4-pro{RESET}")
    print(f"{NEGRITO}  Parsers NLP do Jarvis | {len(CASOS)} casos | {AGORA}{RESET}")
    print(f"{NEGRITO}{'='*70}{RESET}\n")

    acertos = {"gpt-4o": 0, "deepseek": 0}
    total_por_parser = {}
    acertos_por_parser = {"gpt-4o": {}, "deepseek": {}}

    for parser in ["lembrete", "tarefa", "recorrente", "evento"]:
        total_por_parser[parser] = 0
        acertos_por_parser["gpt-4o"][parser] = 0
        acertos_por_parser["deepseek"][parser] = 0

    parser_atual = None

    for mensagem, parser, esperado in CASOS:
        # Cabeçalho do parser quando muda
        if parser != parser_atual:
            parser_atual = parser
            nomes = {"lembrete": "LEMBRETE (pontual)", "tarefa": "TAREFA (checklist)",
                     "recorrente": "RECORRENTE (cron)", "evento": "EVENTO (episódico)"}
            print(f"\n{NEGRITO}{AMARELO}── {nomes[parser]} {'─'*40}{RESET}")

        total_por_parser[parser] += 1
        gpt_r, ds_r = await rodar_caso(mensagem, parser, esperado)

        gpt_ok = checar(gpt_r, esperado)
        ds_ok = checar(ds_r, esperado)

        if gpt_ok:
            acertos["gpt-4o"] += 1
            acertos_por_parser["gpt-4o"][parser] += 1
        if ds_ok:
            acertos["deepseek"] += 1
            acertos_por_parser["deepseek"][parser] += 1

        chave = list(esperado.keys())[0]
        esperado_val = esperado[chave]

        gpt_icon = f"{VERDE}✅{RESET}" if gpt_ok else f"{VERMELHO}❌{RESET}"
        ds_icon = f"{VERDE}✅{RESET}" if ds_ok else f"{VERMELHO}❌{RESET}"

        msg_curta = mensagem[:60] + ("…" if len(mensagem) > 60 else "")
        esperado_str = f"{'TRUE' if esperado_val else 'FALSE'}"

        print(f"  {CINZA}[{esperado_str:5}]{RESET} {msg_curta}")
        print(f"         GPT-4o: {gpt_icon}  {CINZA}{json.dumps(gpt_r, ensure_ascii=False)[:80]}{RESET}")
        print(f"         Flash:  {ds_icon}  {CINZA}{json.dumps(ds_r, ensure_ascii=False)[:80]}{RESET}")

    # ── Resumo final ─────────────────────────────────────────────────────────
    total = len(CASOS)
    pct_gpt = acertos["gpt-4o"] / total * 100
    pct_ds = acertos["deepseek"] / total * 100

    print(f"\n{NEGRITO}{'='*70}{RESET}")
    print(f"{NEGRITO}  RESULTADO FINAL{RESET}")
    print(f"{NEGRITO}{'='*70}{RESET}")
    print(f"  {'Parser':<16} {'GPT-4o':>12} {'DeepSeek v4-pro':>20}")
    print(f"  {'-'*50}")

    for parser in ["lembrete", "tarefa", "recorrente", "evento"]:
        tot = total_por_parser[parser]
        g = acertos_por_parser["gpt-4o"][parser]
        d = acertos_por_parser["deepseek"][parser]
        g_pct = g / tot * 100
        d_pct = d / tot * 100
        cor_d = VERDE if d_pct >= g_pct else VERMELHO
        print(f"  {parser:<16} {g}/{tot} ({g_pct:4.0f}%)   {cor_d}{d}/{tot} ({d_pct:4.0f}%){RESET}")

    print(f"  {'-'*50}")
    cor_total = VERDE if pct_ds >= pct_gpt else VERMELHO
    print(f"  {'TOTAL':<16} {acertos['gpt-4o']}/{total} ({pct_gpt:4.0f}%)   {cor_total}{acertos['deepseek']}/{total} ({pct_ds:4.0f}%){RESET}")
    print(f"\n{NEGRITO}  Critério de aprovação: DeepSeek ≥ 80% E ≤ 2 falhas a mais que GPT-4o{RESET}")

    falhas_extras = acertos["gpt-4o"] - acertos["deepseek"]
    aprovado = pct_ds >= 80 and falhas_extras <= 2

    if aprovado:
        print(f"\n  {VERDE}{NEGRITO}✅ APROVADO — DeepSeek v4-pro pode substituir GPT-4o nos parsers{RESET}")
    else:
        print(f"\n  {VERMELHO}{NEGRITO}❌ REPROVADO — Manter GPT-4o nos parsers{RESET}")
        if pct_ds < 80:
            print(f"  {VERMELHO}   Acurácia {pct_ds:.0f}% abaixo do mínimo de 80%{RESET}")
        if falhas_extras > 2:
            print(f"  {VERMELHO}   {falhas_extras} falhas a mais que o GPT-4o (limite: 2){RESET}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
