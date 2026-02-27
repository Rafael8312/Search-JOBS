import os
import datetime
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# Configurações de API
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def avaliar_vaga_com_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Prompt com REGRAS RÍGIDAS de formatação
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil}
    Vaga: {titulo} na {empresa}.
    Descrição: {descricao[:2000]}

    Instruções Técnicas:
    1. Identifique as competências técnicas da vaga.
    2. Liste quantas o Rafael possui (Perfil vs Vaga).
    3. Calcule o % (Possuídas / Totais da Vaga).
    4. Local: Se a descrição citar cidades brasileiras ou "Brasil", use 'Brasil'. Caso contrário, 'Exterior'.
    5. Regime: Se citar 'Remote', 'Remoto', 'Anywhere' ou 'Home Office', use 'Remoto'. Caso contrário, 'Presencial'.

    Responda APENAS estas 4 linhas sem texto extra:
    PERCENT: [número]
    LOCAL: [Brasil ou Exterior]
    REGIME: [Remoto ou Presencial]
    RESUMO: [Breve justificativa]
    """
    try:
        response = model.generate_content(prompt)
        res = response.text
        
        # Extração por Regex (Garante que o número seja pego mesmo com símbolos)
        percent_match = re.search(r"PERCENT:\s*(\d+)", res)
        score = int(percent_match.group(1)) if percent_match else 0
        
        pais = "Brasil" if "LOCAL: Brasil" in res else "Exterior"
        regime = "Remoto" if "REGIME: Remoto" in res else "Presencial"
        resumo = res.split("RESUMO:")[-1].strip() if "RESUMO:" in res else "Análise concluída."
        
        return score, pais, regime, resumo
    except:
        return 0, "Exterior", "Presencial", "Falha na extração de dados."

def buscar_e_gerar():
    perfil = carregar_perfil()
    # Mix de busca para garantir resultados em ambas as categorias
    queries = [
        {"q": "Analista de BI Brasil", "loc": "Brazil"},
        {"q": "Performance Marketing Brasil", "loc": "Brazil"},
        {"q": "Python Automation Specialist Remote", "loc": None},
        {"q": "Business Intelligence Analyst Worldwide", "loc": None}
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY}
            if item["loc"]:
                params.update({"location": "Brazil", "gl": "br", "hl": "pt-br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    score, pais, regime, resumo = avaliar_vaga_com_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_finais.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local_vaga": v.get("location", "N/D"),
                        "match_score": score,
                        "pais": pais,
                        "regime": regime,
                        "analise": resumo
                    })
        except: continue

    # Template HTML com Filtros de Sub-Nível (Hierárquicos)
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Job Matcher v2</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0a0e17; color: #f1f5f9; }
            .vaga-card { background: #151b28; border: 1px solid #1e293b; transition: 0.2s; }
            .vaga-card:hover { border-color: #3b82f6; }
            .active-btn { background-color: #3b82f6 !important; color: white !important; }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-5xl mx-auto">
            <header class="mb-10 text-center">
                <h1 class="text-4xl font-black mb-2 text-blue-500">Job Intelligence</h1>
                <p class="text-slate-500 text-sm">Organizado por Match de Competências</p>
                
                <div class="mt-8 flex flex-wrap justify-center gap-4 border-b border-slate-800 pb-6">
                    <button onclick="setMainFilter('todos')" id="btn-todos" class="filter-main bg-slate-800 px-6 py-2 rounded-lg font-bold active-btn">Todos</button>
                    <button onclick="setMainFilter('Brasil')" id="btn-Brasil" class="filter-main bg-slate-800 px-6 py-2 rounded-lg font-bold">🇧🇷 Brasil</button>
                    <button onclick="setMainFilter('Exterior')" id="btn-Exterior" class="filter-main bg-slate-800 px-6 py-2 rounded-lg font-bold">🌍 Exterior</button>
                </div>

                <div class="mt-4 flex justify-center gap-4 text-xs">
                    <span class="text-slate-500 uppercase font-bold self-center">Regime:</span>
                    <button onclick="setSubFilter('todos')" id="sub-todos" class="filter-sub bg-slate-900 border border-slate-700 px-3 py-1 rounded active-btn">Qualquer</button>
                    <button onclick="setSubFilter('Remoto')" id="sub-Remoto" class="filter-sub bg-slate-900 border border-slate-700 px-3 py-1 rounded uppercase">Remoto</button>
                    <button onclick="setSubFilter('Presencial')" id="sub-Presencial" class="filter-sub bg-slate-900 border border-slate-700 px-3 py-1 rounded uppercase">Presencial/Híbrido</button>
                </div>
            </header>

            <div id="lista" class="space-y-4">
                {% for v in vagas %}
                <div class="vaga-card p-6 rounded-2xl flex flex-col md:flex-row items-center gap-6" 
                     data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.match_score }}">
                    <div class="flex-1">
                        <div class="flex gap-2 mb-2 text-[10px] font-bold text-blue-400">
                            <span>{{ v.pais }}</span> | <span>{{ v.regime }}</span>
                        </div>
                        <h2 class="text-xl font-bold mb-1">{{ v.titulo }}</h2>
                        <p class="text-slate-400 text-sm mb-4">{{ v.empresa }} — {{ v.local_vaga }}</p>
                        <p class="text-slate-400 text-xs italic">{{ v.analise }}</p>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl font-black text-emerald-500 mb-2">{{ v.match_score }}%</div>
                        <a href="{{ v.link }}" target="_blank" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-xl text-xs font-bold block">Candidatar</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            let mainFilter = 'todos';
            let subFilter = 'todos';

            function setMainFilter(val) {
                mainFilter = val;
                updateUI('.filter-main', 'btn-' + val);
                aplicarFiltros();
            }

            function setSubFilter(val) {
                subFilter = val;
                updateUI('.filter-sub', 'sub-' + val);
                aplicarFiltros();
            }

            function updateUI(selector, activeId) {
                document.querySelectorAll(selector).forEach(b => b.classList.remove('active-btn'));
                document.getElementById(activeId).classList.add('active-btn');
            }

            function aplicarFiltros() {
                const cards = document.querySelectorAll('.vaga-card');
                cards.forEach(card => {
                    let matchMain = (mainFilter === 'todos' || card.dataset.pais === mainFilter);
                    let matchSub = (subFilter === 'todos' || card.dataset.regime === subFilter);
                    card.style.display = (matchMain && matchSub) ? 'flex' : 'none';
                });
            }
            
            // Ordenar por maior match ao carregar
            window.onload = () => {
                const list = document.getElementById('lista');
                const cards = Array.from(list.children);
                cards.sort((a, b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => list.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais))

if __name__ == "__main__":
    buscar_e_gerar()
