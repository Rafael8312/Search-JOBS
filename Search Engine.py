import os
import json
import re
from datetime import datetime
from serpapi import GoogleSearch
from jinja2 import Template

# IA opcional (somente para "insight")
try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

SERP_API_KEY = os.getenv("SERP_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

MAX_PAGINAS_POR_QUERY = int(os.getenv("MAX_PAGINAS_POR_QUERY", "5"))
MAX_VAGAS_PARA_INSIGHT_IA = int(os.getenv("MAX_VAGAS_PARA_INSIGHT_IA", "60"))

# ===== Perfil =====

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Rafael Almeida: Especialista em BI, Python, SQL e Performance Marketing."

# ===== Match local (determinístico) =====

SKILLS = {
    "python": ["python"],
    "sql": ["sql", "t-sql", "postgres", "mysql", "sql server", "bigquery"],
    "power bi": ["power bi", "powerbi"],
    "dax": ["dax"],
    "excel": ["excel"],
    "etl": ["etl", "data pipeline", "pipelines", "airflow", "dbt"],
    "data warehouse": ["data warehouse", "dw", "snowflake", "redshift"],
    "fabric": ["microsoft fabric", "fabric", "lakehouse", "direct lake", "semantic model"],
    "pyspark": ["pyspark", "spark"],
    "data modeling": ["modelagem de dados", "data modeling", "star schema", "kimball"],
    "performance marketing": ["performance marketing", "meta ads", "facebook ads", "google ads", "paid media", "tráfego pago", "trafego pago"],
    "ga4": ["ga4", "google analytics 4", "google analytics"],
}

def extrair_skills(texto: str):
    t = (texto or "").lower()
    found = set()
    for skill, aliases in SKILLS.items():
        if any(a in t for a in aliases):
            found.add(skill)
    return found

def calcular_match_local(perfil_txt: str, titulo: str, descricao: str, localizacao: str):
    vaga_txt = f"{titulo} {descricao} {localizacao}"
    skills_vaga = extrair_skills(vaga_txt)
    skills_perfil = extrair_skills(perfil_txt)

    if not skills_vaga:
        # Sem skills detectadas na vaga -> neutro, evita 0% enganoso
        return 50, sorted(list(skills_perfil)), [], []

    inter = skills_vaga.intersection(skills_perfil)
    match = round((len(inter) / len(skills_vaga)) * 100)
    return match, sorted(list(skills_perfil)), sorted(list(skills_vaga)), sorted(list(inter))

# ===== Remoto (determinístico) =====

def detectar_regime(titulo, descricao, localizacao, extensoes=None):
    texto = f"{titulo} {descricao} {localizacao} {' '.join(extensoes or [])}".lower()
    palavras_remoto = [
        "remote", "remoto", "home office", "work from home",
        "trabalho remoto", "100% remoto", "anywhere", "any location"
    ]
    return "Remoto" if any(p in texto for p in palavras_remoto) else "Presencial"

# ===== Salário (SerpAPI + fallback) =====

def extrair_salario_serpapi(v):
    det = (v.get("detected_extensions") or {})
    if det.get("salary"):
        return det["salary"]

    ext = v.get("extensions") or []
    for e in ext:
        if isinstance(e, str) and any(x in e for x in ["R$", "a year", "per year", "per month", "an hour", "por mês", "por ano", "/mês", "/ano", "K", "k"]):
            return e
    return None

def inferir_senioridade(texto):
    t = (texto or "").lower()
    if any(x in t for x in [" sr", "sênior", "senior", "lead", "principal", "especialista"]):
        return "sr"
    if any(x in t for x in [" pl", "pleno", "mid", "middle"]):
        return "pl"
    if any(x in t for x in [" jr", "júnior", "junior", "entry", "estágio", "intern"]):
        return "jr"
    return "pl"

def faixa_salario_brasil_por_cargo(titulo):
    t = (titulo or "").lower()
    senior = inferir_senioridade(titulo)

    if any(x in t for x in ["bi", "business intelligence", "power bi", "data analyst", "analista de dados"]):
        if senior == "jr":
            return "R$ 5.500 - R$ 8.000"
        if senior == "sr":
            return "R$ 11.500 - R$ 19.300"
        return "R$ 8.500 - R$ 13.500"

    if any(x in t for x in ["performance", "meta ads", "google ads", "tráfego", "trafego", "paid media"]):
        if senior == "jr":
            return "R$ 4.000 - R$ 7.000"
        if senior == "sr":
            return "R$ 10.000 - R$ 18.000"
        return "R$ 7.000 - R$ 12.000"

    if "python" in t and any(x in t for x in ["automation", "automação", "automatizacao", "automacao"]):
        if senior == "sr":
            return "R$ 12.000 - R$ 22.000"
        return "R$ 8.000 - R$ 16.000"

    return "Não informado"

def salario_estimado(v, pais_label):
    s = extrair_salario_serpapi(v)
    if s:
        return s

    titulo = v.get("title", "")
    base = faixa_salario_brasil_por_cargo(titulo)

    if pais_label == "Brasil":
        return base

    if base.startswith("R$"):
        return base + " (estimado p/ Exterior)"
    return "Não informado"

# ===== Link de candidatura =====

def extrair_link_candidatura(v):
    apply_options = v.get("apply_options") or []
    if apply_options and isinstance(apply_options, list):
        link = apply_options[0].get("link")
        if link:
            return link

    if v.get("apply_link"):
        return v["apply_link"]

    related = [
        rl.get("link", "")
        for rl in (v.get("related_links") or [])
        if isinstance(rl, dict) and rl.get("link") and "google.com" not in rl.get("link", "")
    ]
    return related[0] if related else "#"

# ===== SerpAPI paginação =====

def buscar_vagas_serpapi(params_base, max_paginas=5):
    resultados = []
    params = params_base.copy()
    for _ in range(max_paginas):
        search = GoogleSearch(params)
        res = search.get_dict()

        jobs = res.get("jobs_results", []) or []
        resultados.extend(jobs)

        next_token = (res.get("serpapi_pagination") or {}).get("next_page_token")
        if not next_token:
            break
        params["next_page_token"] = next_token
    return resultados

# ===== IA (opcional) só para insight =====

def gerar_insight_ia(perfil, titulo, empresa, descricao, localizacao, match, skills_vaga, skills_inter):
    if not (genai and types and GEMINI_API_KEY):
        return "Match calculado localmente."

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
Gere um insight curto (máx 15 palavras) sobre o match do candidato.
Não recalcule o match.

Match: {match}%
Skills exigidas detectadas: {skills_vaga}
Skills em comum: {skills_inter}

Vaga: {titulo} | {empresa} | {localizacao}
Retorne APENAS JSON: {{"insight":"..."}}
"""
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(resp.text)
        insight = str(data.get("insight", "")).strip()
        return insight[:120] if insight else "Match calculado localmente."
    except Exception as e:
        print(f"[WARN IA] insight falhou: {e}")
        return "Match calculado localmente."

# ===== HTML =====

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>IA Job Finder | Rafael Almeida</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0b0e14] text-slate-300 p-4 md:p-10 font-sans">
  <div class="max-w-4xl mx-auto">
    <header class="text-center mb-12">
      <h1 class="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">JOBS FINDER IA</h1>

      <div class="mt-8 flex flex-wrap justify-center gap-3">
        <button onclick="setPais('todos')" id="p-todos" class="btn bg-blue-600 px-6 py-2 rounded-xl font-bold">Todos</button>
        <button onclick="setPais('Brasil')" id="p-Brasil" class="btn bg-slate-800 px-6 py-2 rounded-xl font-bold">🇧🇷 Brasil</button>
        <button onclick="setPais('Exterior')" id="p-Exterior" class="btn bg-slate-800 px-6 py-2 rounded-xl font-bold">🌍 Exterior</button>
        <div class="flex items-center gap-2 bg-slate-900 px-4 py-2 rounded-xl border border-slate-800 ml-4">
          <input type="checkbox" id="remCheck" onchange="apply()" class="w-4 h-4">
          <label for="remCheck" class="text-xs font-bold text-purple-400 uppercase">Apenas Remoto</label>
        </div>
      </div>

      <div class="mt-6 flex flex-wrap justify-center gap-4 text-sm">
        <span class="bg-slate-800 px-4 py-2 rounded-xl">📋 <span id="cnt-total" class="font-black text-white">0</span> exibidas</span>
        <span class="bg-slate-800 px-4 py-2 rounded-xl">🔎 <span id="cnt-found" class="font-black text-white">{{ total_found }}</span> encontradas</span>
        <span class="bg-slate-800 px-4 py-2 rounded-xl">🇧🇷 <span id="cnt-br" class="font-black text-white">0</span> Brasil</span>
        <span class="bg-slate-800 px-4 py-2 rounded-xl">🌍 <span id="cnt-ext" class="font-black text-white">0</span> Exterior</span>
        <span class="bg-slate-800 px-4 py-2 rounded-xl">🏠 <span id="cnt-rem" class="font-black text-white">0</span> Remoto</span>
      </div>

      <p class="mt-4 text-xs text-slate-500">Atualizado: {{ updated_at }}</p>
    </header>

    <div id="grid-vagas" class="space-y-4">
      {% for v in vagas %}
      <div class="vaga-card bg-[#161b26] p-6 rounded-3xl border border-slate-800 transition hover:border-blue-500"
           data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.score }}">
        <div class="flex flex-col md:flex-row justify-between gap-4">
          <div class="flex-1">
            <div class="flex flex-wrap gap-2 items-center mb-1">
              <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">{{ v.pais }} • {{ v.regime }}</span>
              {% if v.regime == 'Remoto' %}
              <span class="text-[10px] font-black bg-purple-900 text-purple-300 px-2 py-0.5 rounded-full">🏠 REMOTO</span>
              {% endif %}
            </div>

            <h2 class="text-xl font-bold text-white mt-1">{{ v.titulo }}</h2>
            <p class="text-slate-400 text-sm mb-1">{{ v.empresa }} ({{ v.local }})</p>
            <p class="text-yellow-400 text-sm font-bold mb-3">💰 {{ v.salario }}</p>

            <p class="text-slate-300 text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-emerald-500">
              {{ v.analise }}
            </p>

            {% if v.skills_inter %}
            <p class="mt-3 text-xs text-slate-400">
              Skills em comum: {{ v.skills_inter|join(', ') }}
            </p>
            {% endif %}
          </div>

          <div class="text-center md:text-right min-w-[120px]">
            <div class="text-4xl font-black text-emerald-400">{{ v.score }}%</div>
            <div class="text-[10px] text-slate-500 mt-1 uppercase">compatibilidade</div>
            <a href="{{ v.link }}" target="_blank" rel="noopener noreferrer"
               class="block mt-4 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl">
               CANDIDATAR
            </a>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <script>
    let paisF = 'todos';

    function setPais(p) {
      paisF = p;
      document.querySelectorAll('.btn').forEach(b => {
        b.classList.remove('bg-blue-600');
        b.classList.add('bg-slate-800');
      });
      const btn = document.getElementById('p-' + p);
      if (btn) { btn.classList.remove('bg-slate-800'); btn.classList.add('bg-blue-600'); }
      apply();
    }

    function apply() {
      const rem = document.getElementById('remCheck').checked;
      let total = 0, br = 0, ext = 0, remCnt = 0;

      document.querySelectorAll('.vaga-card').forEach(c => {
        if (c.dataset.pais === 'Brasil') br++;
        if (c.dataset.pais === 'Exterior') ext++;
        if (c.dataset.regime === 'Remoto') remCnt++;

        const mP = paisF === 'todos' || c.dataset.pais === paisF;
        const mR = !rem || c.dataset.regime === 'Remoto';
        const visible = mP && mR;

        c.style.display = visible ? 'block' : 'none';
        if (visible) total++;
      });

      document.getElementById('cnt-total').textContent = total;
      document.getElementById('cnt-br').textContent = br;
      document.getElementById('cnt-ext').textContent = ext;
      document.getElementById('cnt-rem').textContent = remCnt;
    }

    window.onload = () => {
      const g = document.getElementById('grid-vagas');
      const cards = Array.from(g.children);
      cards.sort((a, b) => Number(b.dataset.score) - Number(a.dataset.score));
      cards.forEach(c => g.appendChild(c));
      apply();
    }
  </script>
</body>
</html>
"""

# ===== Execução =====

def executar():
    if not SERP_API_KEY:
        raise RuntimeError("SERP_API_KEY não encontrada nos Secrets.")

    perfil = carregar_perfil()

    queries = [
        {"q": "Analista BI",                   "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista Business Intelligence","loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Power BI",                      "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Microsoft Fabric Power BI",     "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista Dados SQL Python",     "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Performance Marketing Meta Ads","loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Gestor Trafego Pago",           "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},

        {"q": "BI Analyst Remote",             "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Business Intelligence Remote",  "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Power BI Developer Remote",     "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Python Automation Specialist Remote","loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Marketing Analytics Remote",    "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
    ]

    vagas_list = []
    vistos = set()
    total_bruto = 0

    for item in queries:
        params_base = {
            "engine": "google_jobs",
            "q": item["q"],
            "api_key": SERP_API_KEY,
            "gl": item.get("gl", "us"),
            "hl": item.get("hl", "en"),
        }
        if item.get("loc"):
            params_base["location"] = item["loc"]

        results = buscar_vagas_serpapi(params_base, max_paginas=MAX_PAGINAS_POR_QUERY)
        total_bruto += len(results)
        print(f"[INFO] '{item['q']}' → {len(results)} vagas brutas")

        for v in results:
            jid = v.get("job_id")
            if not jid or jid in vistos:
                continue
            vistos.add(jid)

            titulo = v.get("title", "")
            empresa = v.get("company_name", "")
            localizacao = v.get("location", "N/D")
            descricao = v.get("description", "")
            extensoes = v.get("extensions") or []

            pais = item["pais_label"]
            regime = detectar_regime(titulo, descricao, localizacao, extensoes)

            link_vaga = extrair_link_candidatura(v)
            salario = salario_estimado(v, pais)

            match, _skills_perfil, skills_vaga, skills_inter = calcular_match_local(
                perfil_txt=perfil,
                titulo=titulo,
                descricao=descricao,
                localizacao=localizacao
            )

            analise = "Match calculado localmente."
            if len(vagas_list) < MAX_VAGAS_PARA_INSIGHT_IA:
                analise = gerar_insight_ia(perfil, titulo, empresa, descricao, localizacao, match, skills_vaga, skills_inter)

            vagas_list.append({
                "titulo": titulo,
                "empresa": empresa,
                "link": link_vaga,
                "local": localizacao,
                "score": match,
                "salario": salario,
                "pais": pais,
                "regime": regime,
                "analise": analise,
                "skills_inter": skills_inter,
            })

    vagas_list.sort(key=lambda x: x.get("score", 0), reverse=True)

    updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = Template(HTML_TEMPLATE).render(
        vagas=vagas_list,
        total_found=len(vagas_list),
        updated_at=updated_at
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[TOTAL] bruto={total_bruto} | unicas={len(vagas_list)} | IA_insights={min(len(vagas_list), MAX_VAGAS_PARA_INSIGHT_IA)}")

if __name__ == "__main__":
    executar()
