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
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil}
    Vaga: {titulo} na {empresa}.
    Descrição: {descricao[:2500]}

    TAREFA:
    1. Analise as competências da vaga vs as do Rafael (Python, BI, Meta Ads, SQL, Telecom).
    2. Responda APENAS uma linha no formato:
    SCORE: [valor de 0 a 100] | LOCAL: [Brasil ou Exterior] | TIPO: [Remoto ou Presencial] | JUSTIFICATIVA: [resumo]
    """
    try:
        response = model.generate_content(prompt)
        res_text = response.text
        # Extração inteligente do Score
        score_match = re.search(r"SCORE:\s*(\d+)", res_text)
        score = int(score_match.group(1)) if score_match else 0
        
        # Extração do Local e Tipo para os filtros
        is_brasil = "Brasil" if "LOCAL: Brasil" in res_text else "Exterior"
        is_remoto = "Remoto" if "Remoto" in res_text or "Remote" in descricao.lower() else "Outros"
        
        return score, is_brasil, is_remoto, res_text
    except:
        return 0, "Exterior", "Outros", "SCORE: 0 | Erro na análise"

def buscar_e_gerar():
    perfil = carregar_perfil()
    # Dobramos as buscas: Metade Brasil, Metade Global
    queries = [
        {"q": "Analista de BI Brasil", "loc": "Brazil"},
        {"q": "Performance Marketing Brasil", "loc": "Brazil"},
        {"q": "Especialista Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation Remote", "loc": None},
        {"q": "Business Intelligence Analyst Remote", "loc": None}
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    for item in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": item["q"],
                "api_key": SERP_API_KEY
            }
            if item["loc"]:
                params["location"] = item["loc"]
                params["gl"] = "br"
                params["hl"] = "pt-br"

            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])
            print(f"🔍 {item['q']}: {len(results)} encontradas.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    score, local, tipo, analise = avaliar_vaga_com_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_finais.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local_vaga": v.get("location", "Não informado"),
                        "match_score": score,
                        "pais_filtro": local,
                        "tipo_filtro": tipo,
                        "analise": analise.split("| JUSTIFICATIVA:")[-1] if "| JUSTIFICATIVA:" in analise else analise
                    })
        except Exception as e:
            print(f"❌ Erro: {e}")

    # Template HTML Moderno com Filtros Dinâmicos
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>IA JOBS | RAFAEL ALMEIDA</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0f172a; color: #f8fafc; font-family: 'Inter', sans-serif; }
            .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
            .card:hover { border-color: #38bdf8; transform: translateY(-2px); }
        </style>
    </head>
    <body class="p-4 md:p-10">
        <div class="max-w-6xl mx-auto">
            <header class="flex flex-col md:row justify-between items-center mb-10 gap-6">
                <div>
                    <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">Job Intelligence</h1>
                    <p class="text-slate-400 mt-2">Análise global de competências para Rafael Almeida</p>
                </div>
                <div class="flex flex-wrap gap-2 justify-center">
                    <button onclick="filterVagas('todos')" class="bg-slate-700 px-4 py-2 rounded-lg text-sm font-bold">Todos</button>
                    <button onclick="filterVagas('Brasil')" class="bg-green-700 px-4 py-2 rounded-lg text-sm font-bold">🇧🇷 Brasil</button>
                    <button onclick="filterVagas('Exterior')" class="bg-blue-700 px-4 py-2 rounded-lg text-sm font-bold">🌍 Exterior</button>
                    <button onclick="filterVagas('Remoto')" class="bg-purple-700 px-4 py-2 rounded-lg text-sm font-bold">🏠 Remoto</button>
                    <select id="sortScore" onchange="sortVagas()" class="bg-slate-800 border border-slate-600 px-4 py-2 rounded-lg text-sm">
                        <option value="desc">Maior Match</option>
                        <option value="asc">Menor Match</option>
                    </select>
                </div>
            </header>

            <div id="container" class="grid gap-4">
                {% for vaga in vagas %}
                <div class="card glass p-6 rounded-2xl transition-all duration-300" 
                     data-pais="{{ vaga.pais_filtro }}" data-tipo="{{ vaga.tipo_filtro }}" data-score="{{ vaga.match_score }}">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <span class="text-[10px] uppercase tracking-widest font-bold text-blue-400">{{ vaga.pais_filtro }} • {{ vaga.tipo_filtro }}</span>
                            <h2 class="text-xl font-bold mt-1 uppercase">{{ vaga.titulo }}</h2>
                            <p class="text-slate-400 text-sm">{{ vaga.empresa }} | {{ vaga.local_vaga }}</p>
                        </div>
                        <div class="text-right">
                            <div class="text-2xl font-black text-emerald-400">{{ vaga.match_score }}%</div>
                            <div class="text-[10px] text-slate-500 uppercase">Compatibilidade</div>
                        </div>
                    </div>
                    <p class="text-slate-300 text-sm leading-relaxed mb-6 border-l-2 border-slate-700 pl-4 italic">
                        {{ vaga.analise }}
                    </p>
                    <a href="{{ vaga.link }}" target="_blank" class="inline-block w-full text-center bg-blue-600 hover:bg-blue-500 py-3 rounded-xl font-bold transition shadow-lg shadow-blue-900/40">Candidatar-se agora</a>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            function filterVagas(tipo) {
                const cards = document.querySelectorAll('.card');
                cards.forEach(card => {
                    card.style.display = 'block';
                    if (tipo === 'Brasil' && card.dataset.pais !== 'Brasil') card.style.display = 'none';
                    if (tipo === 'Exterior' && card.dataset.pais !== 'Exterior') card.style.display = 'none';
                    if (tipo === 'Remoto' && card.dataset.tipo !== 'Remoto') card.style.display = 'none';
                });
            }

            function sortVagas() {
                const container = document.getElementById('container');
                const cards = Array.from(container.getElementsByClassName('card'));
                const order = document.getElementById('sortScore').value;
                
                cards.sort((a, b) => {
                    return order === 'desc' ? b.dataset.score - a.dataset.score : a.dataset.score - b.dataset.score;
                });
                cards.forEach(card => container.appendChild(card));
            }
            window.onload = sortVagas;
        </script>
    </body>
    </html>
    """
    
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais))
    print(f"✅ Sucesso: {len(vagas_finais)} vagas analisadas.")

if __name__ == "__main__":
    buscar_e_gerar()
