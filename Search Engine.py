import os
import datetime
import re
import json
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
    except: return "Perfil não encontrado."

def avaliar_vaga_com_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Forçamos a IA a responder em JSON para evitar erros de leitura
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil[:2000]}
    Vaga: {titulo} | Empresa: {empresa}
    Descrição: {descricao[:1500]}

    Responda APENAS um objeto JSON com estas chaves:
    "percent": (número de 0 a 100 baseado em competências de TI/BI/Marketing do Rafael),
    "local": ("Brasil" ou "Exterior"),
    "regime": ("Remoto" ou "Presencial"),
    "justificativa": (breve texto)
    """
    try:
        response = model.generate_content(prompt)
        # Limpa possíveis marcações de markdown da IA
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)
        return data['percent'], data['local'], data['regime'], data['justificativa']
    except:
        # Plano B caso a IA falhe
        return 50, "Exterior", "Presencial", "Análise simplificada devido a erro de formato."

def buscar_e_gerar():
    perfil = carregar_perfil()
    queries = [
        {"q": "Analista de BI", "loc": "Brazil"},
        {"q": "Performance Marketing Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation Remote", "loc": None}
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY, "num": 10}
            if item["loc"]: params.update({"location": "Brazil", "gl": "br", "hl": "pt-br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                if v.get("job_id") not in vagas_vistas:
                    vagas_vistas.add(v.get("job_id"))
                    score, pais, regime, resumo = avaliar_vaga_com_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_finais.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local_extenso": v.get("location", "N/D"),
                        "match_score": score,
                        "pais": pais,
                        "regime": regime,
                        "analise": resumo
                    })
        except: continue

    # HTML com Subfiltros Reais
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>IA Job Matcher | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0a0e1a; color: #e2e8f0; font-family: sans-serif; }
            .card { background: #161e2d; border: 1px solid #1e293b; transition: 0.3s; display: flex; }
            .card:hover { border-color: #3b82f6; }
            .btn-active { background: #3b82f6 !important; color: white !important; }
        </style>
    </head>
    <body class="p-4 md:p-10">
        <div class="max-w-5xl mx-auto">
            <header class="text-center mb-10">
                <h1 class="text-4xl font-black text-blue-500 mb-2">JOB INTELLIGENCE</h1>
                <p class="text-slate-500 italic">Mais de 15 anos de experiência analisados por IA</p>
                
                <div class="mt-8 flex flex-col gap-4 items-center">
                    <div class="flex gap-2">
                        <button onclick="setPais('todos')" id="p-todos" class="pais-btn bg-slate-800 px-6 py-2 rounded-full text-sm font-bold btn-active">Todos</button>
                        <button onclick="setPais('Brasil')" id="p-Brasil" class="pais-btn bg-slate-800 px-6 py-2 rounded-full text-sm font-bold">🇧🇷 Brasil</button>
                        <button onclick="setPais('Exterior')" id="p-Exterior" class="pais-btn bg-slate-800 px-6 py-2 rounded-full text-sm font-bold">🌍 Exterior</button>
                    </div>
                    <div class="flex gap-4 text-xs text-slate-400">
                        <label><input type="checkbox" id="checkRemoto" onchange="aplicar()"> Apenas Remoto</label>
                    </div>
                </div>
            </header>

            <div id="container" class="space-y-4">
                {% for v in vagas %}
                <div class="card p-6 rounded-2xl flex-col md:flex-row justify-between items-center gap-4" 
                     data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.match_score }}">
                    <div class="flex-1">
                        <div class="text-[10px] font-bold text-blue-400 uppercase mb-1">{{ v.pais }} • {{ v.regime }}</div>
                        <h2 class="text-xl font-bold">{{ v.titulo }}</h2>
                        <p class="text-slate-400 text-sm mb-3">{{ v.empresa }} ({{ v.local_extenso }})</p>
                        <p class="text-slate-300 text-xs bg-black/20 p-3 rounded-lg border-l-2 border-blue-500">{{ v.analise }}</p>
                    </div>
                    <div class="text-center min-w-[100px]">
                        <div class="text-3xl font-black text-emerald-400">{{ v.match_score }}%</div>
                        <a href="{{ v.link }}" target="_blank" class="mt-3 block bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 rounded-lg">VER VAGA</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            let filtroPais = 'todos';
            function setPais(p) {
                filtroPais = p;
                document.querySelectorAll('.pais-btn').forEach(b => b.classList.remove('btn-active'));
                document.getElementById('p-' + p).classList.add('btn-active');
                aplicar();
            }
            function aplicar() {
                const isRemoto = document.getElementById('checkRemoto').checked;
                const cards = document.querySelectorAll('.card');
                cards.forEach(c => {
                    const matchPais = (filtroPais === 'todos' || c.dataset.pais === filtroPais);
                    const matchRemoto = (!isRemoto || c.dataset.regime === 'Remoto');
                    c.style.display = (matchPais && matchRemoto) ? 'flex' : 'none';
                });
            }
            window.onload = () => {
                const container = document.getElementById('container');
                const cards = Array.from(container.children);
                cards.sort((a,b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => container.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    # MUDANÇA IMPORTANTE: Nomeamos como index.html para o GitHub Pages reconhecer como página inicial
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais))

if __name__ == "__main__":
    buscar_e_gerar()
