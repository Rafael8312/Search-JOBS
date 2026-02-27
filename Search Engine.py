import os
import json
import re
from serpapi import GoogleSearch
from google import genai                        # NOVO SDK
from google.genai import types                  # NOVO SDK
from jinja2 import Template

SERP_API_KEY  = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# NOVO SDK: client em vez de configure()
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"              # modelo disponível no novo SDK

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Rafael Almeida: Especialista em BI, Python, SQL e Performance Marketing."

def detectar_regime(titulo, descricao, localizacao):
    texto = f"{titulo} {descricao} {localizacao}".lower()
    palavras_remoto = ["remote", "remoto", "home office", "trabalho remoto",
                       "100% remoto", "anywhere", "híbrido", "hybrid"]
    return "Remoto" if any(p in texto for p in palavras_remoto) else "Presencial"

def analisar_vaga_ia(perfil, titulo, empresa, descricao, localizacao):
    prompt = f"""
Você é um recrutador sênior. Analise a compatibilidade entre o candidato e a vaga.

PERFIL DO CANDIDATO:
{perfil[:1500]}

VAGA:
Título: {titulo}
Empresa: {empresa}
Localização: {localizacao}
Descrição: {descricao[:1000]}

INSTRUÇÕES:
1. Liste as competências exigidas pela vaga.
2. Identifique quais o candidato possui.
3. Calcule: match = (competências que o candidato possui / total exigido) * 100, arredonde para inteiro.
4. Estime a faixa salarial mensal em R$ para este cargo em 2026, considerando empresa e localidade.
5. Escreva um insight de no máximo 15 palavras sobre o match.

Retorne APENAS JSON puro com exatamente estas chaves:
{{"match": <inteiro 0-100>, "salario": "<ex: R$ 8.000 - R$ 12.000>", "insight": "<máximo 15 palavras>"}}
"""
    response_text = ""
    try:
        # NOVO SDK com JSON mode garantido
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        response_text = response.text
        data = json.loads(response_text)
        return (
            int(data.get('match', 0)),
            str(data.get('salario', 'Não estimado')),
            str(data.get('insight', 'Análise inconclusiva.'))
        )
    except json.JSONDecodeError as e:
        # Fallback: tenta extrair JSON mesmo com lixo ao redor
        json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return int(data.get('match', 0)), str(data.get('salario', 'N/D')), str(data.get('insight', ''))
            except:
                pass
        print(f"[ERRO JSON] {titulo} | {e} | Resposta: {response_text[:200]}")
        return 0, "Não estimado", "Erro ao interpretar resposta da IA."
    except Exception as e:
        # CORRIGIDO: response_text inicializado antes, sem UnboundLocalError
        print(f"[ERRO IA] {titulo} | {e} | Resposta: {response_text[:200]}")
        return 0, "Não estimado", "Erro técnico na análise."

def buscar_vagas_serpapi(params_base, max_paginas=5):
    resultados = []
    params = params_base.copy()
    for _ in range(max_paginas):
        try:
            search = GoogleSearch(params)
            res = search.get_dict()
            jobs = res.get("jobs_results", [])
            resultados.extend(jobs)
            next_token = res.get("serpapi_pagination", {}).get("next_page_token")
            if not next_token:
                break
            params["next_page_token"] = next_token
        except Exception as e:
            print(f"[ERRO SERPAPI] {e}")
            break
    return resultados

def executar():
    perfil = carregar_perfil()

    queries = [
        # Brasil
        {"q": "Analista BI",                         "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista Business Intelligence",       "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista BI Pleno Senior",            "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Performance Marketing Meta Ads",       "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Gestor Trafego Pago",                 "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista Marketing Digital",           "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Analista Dados SQL Python",           "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "BI Developer Power BI",               "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Data Analyst Python",                 "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        # Exterior / Remoto
        {"q": "BI Analyst Remote",                   "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Business Intelligence Remote",        "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Performance Marketing Remote",        "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Python Automation Specialist Remote", "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Data Analyst Remote SQL Python",      "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Marketing Analytics Remote",          "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
    ]

    vagas_list = []
    vistos = set()

    for item in queries:
        params_base = {
            "engine": "google_jobs",
            "q": item["q"],
            "api_key": SERP_API_KEY,
            "gl": item.get("gl", "us"),
            "hl": item.get("hl", "en"),
        }
        if item["loc"]:
            params_base["location"] = item["loc"]

        results = buscar_vagas_serpapi(params_base, max_paginas=5)
        print(f"[INFO] '{item['q']}' → {len(results)} vagas brutas")

        for v in results:
            jid = v.get("job_id")
            if not jid or jid in vistos:
                continue
            vistos.add(jid)

            titulo      = v.get('title', '')
            empresa     = v.get('company_name', '')
            localizacao = v.get("location", "N/D")
            descricao   = v.get("description", "")
            regime      = detectar_regime(titulo, descricao, localizacao)

            apply_options = v.get("apply_options", [])
            if apply_options:
                link_vaga = apply_options[0].get("link", "#")
            else:
                related = [
                    rl.get("link", "")
                    for rl in v.get("related_links", [])
                    if "google.com" not in rl.get("link", "")
                ]
                link_vaga = related[0] if related else "#"

            m, salario, mot = analisar_vaga_ia(perfil, titulo, empresa, descricao, localizacao)

            vagas_list.append({
                "titulo": titulo, "empresa": empresa,
                "link": link_vaga, "local": localizacao,
                "score": m, "salario": salario,
                "pais": item["pais_label"],
                "regime": regime, "analise": mot
            })

    print(f"[TOTAL] {len(vagas_list)} vagas únicas processadas.")

    html_template = """
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
                    <span class="bg-slate-800 px-4 py-2 rounded-xl">📋 <span id="cnt-total" class="font-black text-white">0</span> vagas exibidas</span>
                    <span class="bg-slate-800 px-4 py-2 rounded-xl">🇧🇷 <span id="cnt-br" class="font-black text-white">0</span> Brasil</span>
                    <span class="bg-slate-800 px-4 py-2 rounded-xl">🌍 <span id="cnt-ext" class="font-black text-white">0</span> Exterior</span>
                    <span class="bg-slate-800 px-4 py-2 rounded-xl">🏠 <span id="cnt-rem" class="font-black text-white">0</span> Remoto</span>
                </div>
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
                            <p class="text-yellow-400 text-sm font-bold mb-4">💰 {{ v.salario }}</p>
                            <p class="text-slate-300 text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-emerald-500">{{ v.analise }}</p>
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
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_list))

if __name__ == "__main__":
    executar()
