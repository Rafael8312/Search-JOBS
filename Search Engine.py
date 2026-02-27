import os
import json
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# APIs - Certifique-se que estas variáveis estão no Secrets do GitHub
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Rafael Almeida: Especialista em BI, Python, SQL e Performance Marketing."

def analisar_vaga_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Forçamos a IA a ignorar conversas e cuspir apenas JSON puro
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil[:1500]}
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Responda APENAS um objeto JSON exatamente assim:
    {{
      "match": (número de 0 a 100),
      "pais": ("Brasil" ou "Exterior"),
      "regime": ("Remoto" or "Presencial"),
      "insight": (máximo 15 palavras sobre o match)
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza para garantir que pegamos apenas o JSON, mesmo que a IA mande lixo
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data['match'], data['pais'], data['regime'], data['insight']
        return 50, "Exterior", "Presencial", "Análise inconclusiva."
    except:
        return 0, "Exterior", "Presencial", "Erro técnico na análise."

def executar():
    perfil = carregar_perfil()
    queries = [
        {"q": "Analista de BI Brasil", "loc": "Brazil"},
        {"q": "Performance Marketing Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation Specialist Remote", "loc": None}
    ]
    
    vagas_list = []
    vistos = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY}
            if item["loc"]: 
                params.update({"location": "Brazil", "gl": "br", "hl": "pt-br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                jid = v.get("job_id")
                if jid and jid not in vistos:
                    vistos.add(jid)
                    # Busca o link real de candidatura (resolve o problema de abrir o programa)
                    link_vaga = v.get("related_links", [{}])[0].get("link", v.get("apply_link", "#"))
                    
                    m, p, r, mot = analisar_vaga_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_list.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": link_vaga,
                        "local": v.get("location", "N/D"),
                        "score": m, "pais": p, "regime": r, "analise": mot
                    })
        except: continue

    # HTML com filtros funcionando via JS (resolve o problema de filtros vazios)
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
            </header>

            <div id="grid-vagas" class="space-y-4">
                {% for v in vagas %}
                <div class="vaga-card bg-[#161b26] p-6 rounded-3xl border border-slate-800 transition hover:border-blue-500" 
                     data-pais="{{v.pais}}" data-regime="{{v.regime}}" data-score="{{v.score}}">
                    <div class="flex flex-col md:flex-row justify-between gap-4">
                        <div class="flex-1">
                            <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">{{v.pais}} • {{v.regime}}</span>
                            <h2 class="text-xl font-bold text-white mt-1">{{v.titulo}}</h2>
                            <p class="text-slate-400 text-sm mb-4">{{v.empresa}} ({{v.local}})</p>
                            <p class="text-slate-300 text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-emerald-500">{{v.analise}}</p>
                        </div>
                        <div class="text-center md:text-right min-w-[120px]">
                            <div class="text-4xl font-black text-emerald-400">{{v.score}}%</div>
                            <a href="{{v.link}}" target="_blank" class="block mt-4 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl">CANDIDATAR</a>
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
                document.querySelectorAll('.btn').forEach(b => b.classList.replace('bg-blue-600', 'bg-slate-800'));
                document.getElementById('p-' + p).classList.replace('bg-slate-800', 'bg-blue-600');
                apply();
            }
            function apply() {
                const rem = document.getElementById('remCheck').checked;
                document.querySelectorAll('.vaga-card').forEach(c => {
                    const mP = paisF === 'todos' || c.dataset.pais === paisF;
                    const mR = !rem || c.dataset.regime === 'Remoto';
                    c.style.display = (mP && mR) ? 'block' : 'none';
                });
            }
            window.onload = () => {
                const g = document.getElementById('grid-vagas');
                const cards = Array.from(g.children);
                cards.sort((a,b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => g.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    # CRÍTICO: Deve-se chamar index.html para o GitHub Pages carregar o link direto
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_list))

if __name__ == "__main__":
    executar()
