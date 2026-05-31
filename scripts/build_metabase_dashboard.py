"""
Monta o dashboard de BI no Metabase via API REST.

Cria os cards (perguntas SQL nativas) dos KPIs do projeto RAG e os organiza
num dashboard com layout pronto. Idempotente o suficiente para uso único:
re-rodar cria um novo dashboard com sufixo de versão.

Uso:
    SESSION=<token> DB_ID=2 python scripts/build_metabase_dashboard.py
"""
import json
import os
import urllib.request

BASE = os.environ.get("MB_URL", "http://localhost:3001")
SESSION = os.environ["SESSION"]
DB_ID = int(os.environ.get("DB_ID", "2"))


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "X-Metabase-Session": SESSION},
    )
    with urllib.request.urlopen(req) as r:
        body = r.read().decode()
        return json.loads(body) if body else {}


def card(name, sql, display, viz=None):
    payload = {
        "name": name,
        "type": "question",
        "dataset_query": {"type": "native", "native": {"query": sql}, "database": DB_ID},
        "display": display,
        "visualization_settings": viz or {},
        "collection_id": None,
    }
    res = api("POST", "/api/card", payload)
    print(f"  card #{res['id']:>3}  {name}")
    return res["id"]


# ---- KPIs (scalars) -------------------------------------------------
c_total = card(
    "Total de Conversas",
    "SELECT count(*) AS total FROM conversation_logs",
    "scalar",
)
c_defl = card(
    "Deflection Rate (%)",
    "SELECT round(100.0 * count(*) FILTER (WHERE not_found = false) / count(*), 1) "
    "AS deflection_rate FROM conversation_logs",
    "scalar",
    {"column_settings": {'["name","deflection_rate"]': {"number_style": "decimal", "suffix": "%"}}},
)
c_sat = card(
    "Satisfação (% útil)",
    "SELECT round(100.0 * count(*) FILTER (WHERE rating = 'useful') / "
    "NULLIF(count(*) FILTER (WHERE rating IS NOT NULL), 0), 1) AS satisfacao "
    "FROM conversation_logs",
    "scalar",
    {"column_settings": {'["name","satisfacao"]': {"suffix": "%"}}},
)
c_tmpr = card(
    "TMPR — Tempo Médio de Resposta (s)",
    "SELECT round(avg(response_time_ms) / 1000.0, 2) AS tmpr_seg FROM conversation_logs",
    "scalar",
    {"column_settings": {'["name","tmpr_seg"]': {"suffix": " s"}}},
)

# ---- Séries / distribuições ----------------------------------------
c_dia = card(
    "Volume de Conversas por Dia",
    "SELECT date_trunc('day', created_at)::date AS dia, count(*) AS conversas "
    "FROM conversation_logs GROUP BY 1 ORDER BY 1",
    "line",
    {"graph.dimensions": ["dia"], "graph.metrics": ["conversas"]},
)
c_fb = card(
    "Distribuição de Feedback",
    "SELECT CASE rating WHEN 'useful' THEN 'Útil' WHEN 'not_useful' THEN 'Não útil' "
    "ELSE 'Sem avaliação' END AS avaliacao, count(*) AS qtd "
    "FROM conversation_logs GROUP BY 1 ORDER BY 2 DESC",
    "pie",
    {"pie.dimension": "avaliacao", "pie.metric": "qtd"},
)
c_sla = card(
    "Tempo de Resposta por Faixa (SLA 5s)",
    "SELECT CASE WHEN response_time_ms <= 2000 THEN '0-2s' "
    "WHEN response_time_ms <= 3000 THEN '2-3s' "
    "WHEN response_time_ms <= 4000 THEN '3-4s' "
    "WHEN response_time_ms <= 5000 THEN '4-5s' "
    "ELSE '> 5s (fora do SLA)' END AS faixa, count(*) AS qtd "
    "FROM conversation_logs GROUP BY 1 ORDER BY 1",
    "bar",
    {"graph.dimensions": ["faixa"], "graph.metrics": ["qtd"]},
)
c_doc = card(
    "Documentos Mais Citados",
    "SELECT source_filename AS documento, count(*) AS citacoes "
    "FROM conversation_logs WHERE source_filename IS NOT NULL "
    "GROUP BY 1 ORDER BY 2 DESC",
    "row",
    {"graph.dimensions": ["documento"], "graph.metrics": ["citacoes"]},
)
c_cli = card(
    "Conversas por Cliente",
    "SELECT u.email AS cliente, count(*) AS conversas "
    "FROM conversation_logs c JOIN users u ON u.id = c.user_id "
    "GROUP BY 1 ORDER BY 2 DESC",
    "row",
    {"graph.dimensions": ["cliente"], "graph.metrics": ["conversas"]},
)

# ---- Dashboard ------------------------------------------------------
dash = api("POST", "/api/dashboard", {
    "name": "Painel de Suporte RAG — Cancella Informática",
    "description": "KPIs do assistente de suporte Nível 1: deflection, satisfação, "
                   "TMPR e volume. Fonte: conversation_logs (PostgreSQL).",
})
dash_id = dash["id"]
print(f"\n  dashboard #{dash_id}  {dash['name']}")

# Layout em grade de 24 colunas
dashcards = [
    # linha 0 — 4 scalars (6 col cada)
    {"id": -1, "card_id": c_total, "row": 0, "col": 0,  "size_x": 6, "size_y": 3},
    {"id": -2, "card_id": c_defl,  "row": 0, "col": 6,  "size_x": 6, "size_y": 3},
    {"id": -3, "card_id": c_sat,   "row": 0, "col": 12, "size_x": 6, "size_y": 3},
    {"id": -4, "card_id": c_tmpr,  "row": 0, "col": 18, "size_x": 6, "size_y": 3},
    # linha 1 — série temporal (largura total)
    {"id": -5, "card_id": c_dia,   "row": 3, "col": 0,  "size_x": 24, "size_y": 6},
    # linha 2 — feedback + faixas de tempo
    {"id": -6, "card_id": c_fb,    "row": 9, "col": 0,  "size_x": 12, "size_y": 6},
    {"id": -7, "card_id": c_sla,   "row": 9, "col": 12, "size_x": 12, "size_y": 6},
    # linha 3 — documentos + clientes
    {"id": -8, "card_id": c_doc,   "row": 15, "col": 0,  "size_x": 12, "size_y": 6},
    {"id": -9, "card_id": c_cli,   "row": 15, "col": 12, "size_x": 12, "size_y": 6},
]
api("PUT", f"/api/dashboard/{dash_id}", {"dashcards": dashcards})
print(f"\n  OK -> {BASE}/dashboard/{dash_id}")
