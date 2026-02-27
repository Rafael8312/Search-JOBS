import os
import datetime
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# Configurações
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
    # Limitamos a descrição para 1500 caracteres para agilizar o processamento
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil}
    Vaga: {titulo} na {empresa}.
    Descrição: {descricao[:1500]}

    Instruções:
    1. Identifique as competências pedidas e compare com as do Rafael.
    2. Calcule o % de match (Competências do Rafael / Competências da Vaga).
    3. Identifique se o local é 'Brasil' ou 'Exterior'.
    4. Identifique se é 'Remoto' ou 'Presencial/Híbrido'.

    Responda EXATAMENTE neste formato:
    MATCH_PERCENT: [número]
    LOCAL: [Brasil/Exterior]
    REGIME: [Remoto/Presencial]
    MOTIVO: [Breve resumo]
    """
    try:
        response = model.generate_content(prompt)
        res = response.text
        
        # Extração Robusta
        score = int(re.search(r"MATCH_PERCENT:\s*(\d+)", res).group(1)) if re.search(r"MATCH_PERCENT:\s*(\d+)", res) else 0
        pais = "Brasil" if "LOCAL: Brasil" in res else "Exterior"
        regime = "Remoto" if "REGIME: Remoto" in res else "Presencial"
        motivo = res.split("MOTIVO:")[-1].strip() if "MOTIVO:" in res else "Análise concluída."
        
        return score, pais, regime, motivo
    except:
        return 0, "Exterior", "Presencial", "Erro na análise de dados."

def buscar_e_gerar():
    perfil = carregar_perfil()
    # Otimização de Queries para cobrir Brasil e Mundo
    queries = [
        {"q": "Analista de BI", "loc": "Brazil"},
        {"q": "Performance Marketing", "loc": "Brazil"},
        {"q": "Python Automation Specialist", "loc": None},
        {"q": "Business Intelligence Analyst Remote", "loc": None}
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY, "num": 10}
            if item["loc"]:
                params.update({"location": "Brazil", "gl": "br", "hl": "pt-br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    score, pais, regime, motivo = avaliar_vaga_com_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_finais.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local_vaga": v.get("location", "N/D"),
                        "match_score": score,
                        "pais": pais,
                        "regime": regime,
                        "analise": motivo
                    })
        except: continue

    # Template HTML com Filtros Corrigidos e UI Melhorada
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job Intelligence AI</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Plus Jakarta Sans', sans-serif; background: #0b0f1a; color: #e2e8f0; }
            .vaga-card { background: rgba(23, 30, 48, 0.6); border: 1px solid rgba(255,255,255,0.05); transition: 0.3s; }
            .vaga-card:hover { border-color: #3b82f6; transform: translateY(-3px); background: rgba(23, 30, 48, 0.9); }
            .badge-match { background: linear-gradient(135deg, #3b82f6, #2dd4bf); }
        </style>
    </head>
    <body class="p-6">
        <div class="max-w-5xl mx-auto">
            <header class="text-center mb-12">
                <h1 class="text-5xl font-extrabold mb-4 bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">Job Intelligence</h1>
                <p class="text-slate-400 uppercase tracking-widest text-xs font-bold">Análise em tempo real para Rafael Almeida</p>
                
                <div class="mt-8 flex flex-wrap justify-center gap-3">
                    <button onclick="filtrar('todos', 'todos')" class="bg-slate-800 px-6 py-2 rounded-full font-bold hover:bg-slate-700">Todos</button>
                    <button onclick="filtrar('Brasil', 'todos')" class="bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 px-6 py-2 rounded-full font-bold hover:bg-emerald-600/40">🇧🇷 Brasil</button>
                    <button onclick="filtrar('Exterior', 'todos')" class="bg-blue-600/20 text-blue-400 border border-blue-600/30 px-6 py-2 rounded-full font-bold hover:bg-blue-600/40">🌍 Exterior</button>
                    <button onclick="filtrar('todos', 'Remoto')" class="bg-purple-600/20 text-purple-400 border border-purple-600/30 px-6 py-2 rounded-full font-bold hover:bg-purple-600/40">🏠 Somente Remoto</button>
                </div>
            </header>

            <div id="lista" class="grid gap-6">
                {% for v in vagas %}
                <div class="vaga-card p-6 rounded-3xl" data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.match_score }}">
                    <div class="flex flex-col md:flex-row justify-between gap-4">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2 text-[10px] font-bold uppercase tracking-tighter">
                                <span class="text-blue-400">{{ v.pais }}</span>
                                <span class="text-slate-600">•</span>
                                <span class="text-purple-400">{{ v.regime }}</span>
                            </div>
                            <h2 class="text-xl font-bold text-white mb-1">{{ v.titulo }}</h2>
                            <p class="text-slate-400 text-sm mb-4">{{ v.empresa }} — {{ v.local_vaga }}</p>
                            <p class="text-slate-300 text-sm italic bg-black/20 p-4 rounded-2xl">{{ v.analise }}</p>
                        </div>
                        <div class="text-center md:text-right flex flex-col justify-between">
                            <div class="badge-match w-20 h-20 rounded-2xl flex flex-col items-center justify-center mx-auto md:ml-auto">
                                <span class="text-2xl font-black text-white">{{ v.match_score }}%</span>
                                <span class="text-[8px] text-white/80 font-bold uppercase">Match</span>
                            </div>
                            <a href="{{ v.link }}" target="_blank" class="mt-4 bg-white text-black px-6 py-2 rounded-xl font-bold text-sm hover:bg-blue-400 transition">Ver Vaga</a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            function filtrar(pais, regime) {
                const cards = document.querySelectorAll('.vaga-card');
                cards.forEach(card => {
                    let show = true;
                    if (pais !== 'todos' && card.dataset.pais !== pais) show = false;
                    if (regime !== 'todos' && card.dataset.regime !== regime) show = false;
                    card.style.display = show ? 'block' : 'none';
                });
            }
        </script>
    </body>
    </html>
    """
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais))

if __name__ == "__main__":
    buscar_e_gerar()
