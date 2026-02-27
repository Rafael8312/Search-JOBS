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
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thryken Search Jobs</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: 'Segoe UI', sans-serif; }
    .btn-active { background: #e5e7eb !important; color: #111827 !important; }
    .card-hover:hover { border-color: #9ca3af; }
  </style>
</head>
<body class="bg-[#1a1a1a] text-[#d1d5db] p-4 md:p-10">
  <div class="max-w-4xl mx-auto">

    <!-- HEADER -->
    <header class="text-center mb-12">

      <!-- Logo + Título -->
      <div class="flex flex-col items-center gap-4 mb-6">
        <img src="https://i.ibb.co/qYRc7DZ7/logo-thryken.png"
             alt="Thryken"
             class="h-20 w-auto object-contain"
             onerror="this.style.display='none'">
        <h1 class="text-4xl font-black tracking-tight text-white uppercase">
          Thryken Search Jobs
        </h1>
      </div>

      <!-- Filtros -->
      <div class="mt-4 flex flex-wrap justify-center gap-3">
        <button onclick="setPais('todos')" id="p-todos"
                class="btn bg-[#e5e7eb] text-[#111827] px-6 py-2 rounded-xl font-bold">Todos</button>
        <button onclick="setPais('Brasil')" id="p-Brasil"
                class="btn bg-[#2d2d2d] text-[#d1d5db] px-6 py-2 rounded-xl font-bold border border-[#3f3f3f]">🇧🇷 Brasil</button>
        <button onclick="setPais('Exterior')" id="p-Exterior"
                class="btn bg-[#2d2d2d] text-[#d1d5db] px-6 py-2 rounded-xl font-bold border border-[#3f3f3f]">🌍 Exterior</button>
        <div class="flex items-center gap-2 bg-[#2d2d2d] px-4 py-2 rounded-xl border border-[#3f3f3f] ml-2">
          <input type="checkbox" id="remCheck" onchange="apply()" class="w-4 h-4 accent-white">
          <label for="remCheck" class="text-xs font-bold text-[#9ca3af] uppercase">Apenas Remoto</label>
        </div>
      </div>

      <!-- Contadores -->
      <div class="mt-6 flex flex-wrap justify-center gap-3 text-sm">
        <span class="bg-[#2d2d2d] border border-[#3f3f3f] px-4 py-2 rounded-xl">
          📋 <span id="cnt-total" class="font-black text-white">0</span> exibidas
        </span>
        <span class="bg-[#2d2d2d] border border-[#3f3f3f] px-4 py-2 rounded-xl">
          🔎 <span class="font-black text-white">{{ total_found }}</span> encontradas
        </span>
        <span class="bg-[#2d2d2d] border border-[#3f3f3f] px-4 py-2 rounded-xl">
          🇧🇷 <span id="cnt-br" class="font-black text-white">0</span> Brasil
        </span>
        <span class="bg-[#2d2d2d] border border-[#3f3f3f] px-4 py-2 rounded-xl">
          🌍 <span id="cnt-ext" class="font-black text-white">0</span> Exterior
        </span>
        <span class="bg-[#2d2d2d] border border-[#3f3f3f] px-4 py-2 rounded-xl">
          🏠 <span id="cnt-rem" class="font-black text-white">0</span> Remoto
        </span>
      </div>

      <p class="mt-4 text-xs text-[#6b7280]">Atualizado: {{ updated_at }}</p>
    </header>

    <!-- VAGAS -->
    <div id="grid-vagas" class="space-y-4">
      {% for v in vagas %}
      <div class="vaga-card bg-[#222222] p-6 rounded-3xl border border-[#3f3f3f] transition card-hover"
           data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.score }}">
        <div class="flex flex-col md:flex-row justify-between gap-4">
          <div class="flex-1">

            <div class="flex flex-wrap gap-2 items-center mb-1">
              <span class="text-[10px] font-black text-[#9ca3af] uppercase tracking-widest">
                {{ v.pais }} • {{ v.regime }}
              </span>
              {% if v.regime == 'Remoto' %}
              <span class="text-[10px] font-black bg-[#374151] text-[#d1d5db] px-2 py-0.5 rounded-full">🏠 REMOTO</span>
              {% endif %}
            </div>

            <h2 class="text-xl font-bold text-white mt-1">{{ v.titulo }}</h2>
            <p class="text-[#9ca3af] text-sm mb-1">{{ v.empresa }} ({{ v.local }})</p>
            <p class="text-[#fbbf24] text-sm font-bold mb-3">💰 {{ v.salario }}</p>

            <p class="text-[#d1d5db] text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-[#6b7280]">
              {{ v.analise }}
            </p>

            {% if v.skills_inter %}
            <p class="mt-3 text-xs text-[#9ca3af]">
              ✅ Skills em comum: <span class="text-white">{{ v.skills_inter|join(', ') }}</span>
            </p>
            {% endif %}
          </div>

          <div class="text-center md:text-right min-w-[130px]">
            <div class="text-4xl font-black text-white">{{ v.score }}%</div>
            <div class="text-[10px] text-[#6b7280] mt-1 uppercase">compatibilidade</div>
            <a href="{{ v.link }}" target="_blank" rel="noopener noreferrer"
               class="block mt-4 bg-white hover:bg-[#e5e7eb] text-[#111827] font-bold py-3 rounded-xl transition">
              CANDIDATAR
            </a>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>

    <!-- FOOTER -->
    <footer class="text-center mt-16 pb-8 text-xs text-[#6b7280] space-y-2">
      <p>Desenvolvido por <span class="text-white font-bold">Rafael Almeida</span></p>
      <p>
        <a href="https://wa.me/5532984489364" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 text-[#9ca3af] hover:text-white transition font-medium">
          <!-- WhatsApp SVG icon -->
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="w-4 h-4 fill-current">
            <path d="M16 0C7.163 0 0 7.163 0 16c0 2.827.737 5.48 2.027 7.784L0 32l8.395-2.003A15.94 15.94 0 0 0 16 32c8.837 0 16-7.163 16-16S24.837 0 16 0zm0 29.333a13.27 13.27 0 0 1-6.773-1.85l-.486-.289-4.985 1.189 1.237-4.858-.317-.499A13.267 13.267 0 0 1 2.667 16C2.667 8.637 8.637 2.667 16 2.667S29.333 8.637 29.333 16 23.363 29.333 16 29.333zm7.273-9.927c-.397-.199-2.35-1.159-2.715-1.292-.365-.133-.63-.199-.895.199-.265.397-1.027 1.292-1.259 1.557-.232.265-.464.298-.861.1-.397-.199-1.676-.618-3.193-1.972-1.18-1.052-1.977-2.351-2.208-2.748-.232-.397-.025-.611.174-.809.179-.178.397-.464.596-.696.199-.232.265-.397.397-.662.133-.265.066-.497-.033-.696-.099-.199-.895-2.158-1.226-2.955-.323-.775-.651-.67-.895-.682l-.762-.013c-.265 0-.696.099-1.061.497-.365.397-1.391 1.358-1.391 3.313 0 1.955 1.424 3.844 1.623 4.109.199.265 2.802 4.278 6.788 5.998.949.41 1.689.654 2.266.838.952.303 1.818.26 2.502.158.763-.114 2.35-.96 2.682-1.889.332-.928.332-1.724.232-1.889-.099-.166-.365-.265-.762-.464z"/>
          </svg>
          +55 (32) 9 8448-9364
        </a>
      </p>
    </footer>

  </div>

  <script>
    let paisF = 'todos';

    function setPais(p) {
      paisF = p;
      document.querySelectorAll('.btn').forEach(b => {
        b.classList.remove('bg-[#e5e7eb]', 'text-[#111827]');
        b.classList.add('bg-[#2d2d2d]', 'text-[#d1d5db]');
      });
      const btn = document.getElementById('p-' + p);
      if (btn) {
        btn.classList.remove('bg-[#2d2d2d]', 'text-[#d1d5db]');
        btn.classList.add('bg-[#e5e7eb]', 'text-[#111827]');
      }
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

    from datetime import timezone, timedelta
    tz_sp = timezone(timedelta(hours=-3))
    updated_at = datetime.now(tz=tz_sp).strftime("%d/%m/%Y %H:%M (horário de Brasília)")

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


