import os
import json
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
    except: return "Perfil não encontrado."

def analisar_vaga_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Forçamos a IA a ignorar conversas e cuspir apenas JSON
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil[:1500]}
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Responda APENAS um objeto JSON estrito com estas chaves:
    "match": (inteiro de 0 a 100),
    "localizacao": ("Brasil" ou "Exterior"),
    "modalidade": ("Remoto" ou "Presencial"),
    "insight": (texto de 10 palavras sobre o match)
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza de markdown caso a IA coloque
        json_clean = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_clean)
        return data['match'], data['localizacao'], data['modalidade'], data['insight']
    except:
        return 0, "Exterior", "Presencial", "Erro na análise de dados."

def gerar_painel():
    perfil = carregar_perfil()
    queries = [
        {"q": "Analista de BI Brasil", "loc": "Brazil"},
        {"q": "Performance Marketing Remote", "loc": None}
    ]
    
    vagas_processadas = []
    vistos = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY}
            if item["loc"]: params.update({"location": "Brazil", "gl": "br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                if v.get("job_id") not in vistos:
                    vistos.add(v.get("job_id"))
                    m, l, mod, ins = analisar_vaga_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_processadas.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "cidade": v.get("location", "N/D"),
                        "match": m, "pais": l, "regime": mod, "motivo": ins
                    })
        except: continue

    # HTML com Hierarquia de Filtros Corrigida
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Job Intelligence AI</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-[#0a0c14] text-white p-8">
        <div class="max-w-4xl mx-auto">
            <header class="text-center mb-10">
                <h1 class="text-3xl font-bold text-cyan-400">Job Intelligence</h1>
                <p class="text-gray-500 text-sm">Filtros Inteligentes para Rafael Almeida</p>
                
                <div class="mt-8 flex flex-col gap-4 items-center">
                    <div class="flex gap-2">
                        <button onclick="setPais('todos')" id="b-todos" class="p-btn bg-gray-800 px-5 py-2 rounded-lg font-bold">Todos</button>
                        <button onclick="setPais('Brasil')" id="b-Brasil" class="p-btn bg-gray-800 px-5 py-2 rounded-lg font-bold">🇧🇷 Brasil</button>
                        <button onclick="setPais('Exterior')" id="b-Exterior" class="p-btn bg-gray-800 px-5 py-2 rounded-lg font-bold">🌍 Exterior</button>
                    </div>
                    <div class="flex gap-4 text-xs">
                        <label class="flex items-center gap-2 text-purple-400">
                            <input type="checkbox" id="remotoOnly" onchange="aplicar()"> SOMENTE REMOTO
                        </label>
                    </div>
                </div>
            </header>

            <div id="grid" class="space-y-4">
                {% for v in vagas %}
                <div class="job-card bg-[#151926] p-6 rounded-2xl border border-gray-800" 
                     data-pais="{{v.pais}}" data-regime="{{v.regime}}" data-score="{{v.match}}">
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-[10px] font-bold text-cyan-500 uppercase">{{v.pais}} | {{v.regime}}</span>
                            <h2 class="text-xl font-bold">{{v.titulo}}</h2>
                            <p class="text-gray-400 text-sm">{{v.empresa}} — {{v.cidade}}</p>
                        </div>
                        <div class="text-right">
                            <div class="text-2xl font-black text-emerald-400">{{v.match}}%</div>
                            <a href="{{v.link}}" target="_blank" class="mt-3 inline-block bg-blue-600 hover:bg-blue-500 px-4 py-1 rounded text-xs font-bold">CANDIDATAR</a>
                        </div>
                    </div>
                    <p class="mt-4 text-xs text-gray-400 italic">{{v.motivo}}</p>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            let filtroPais = 'todos';
            function setPais(p) {
                filtroPais = p;
                document.querySelectorAll('.p-btn').forEach(b => b.classList.remove('bg-blue-600'));
                document.getElementById('b-' + p).classList.add('bg-blue-600');
                aplicar();
            }
            function aplicar() {
                const remoto = document.getElementById('remotoOnly').checked;
                document.querySelectorAll('.job-card').forEach(c => {
                    const mPais = filtroPais === 'todos' || c.dataset.pais === filtroPais;
                    const mRegime = !remoto || c.dataset.regime === 'Remoto';
                    c.style.display = (mPais && mRegime) ? 'block' : 'none';
                });
            }
            window.onload = () => {
                setPais('todos');
                const g = document.getElementById('grid');
                const cards = Array.from(g.children);
                cards.sort((a,b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => g.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    # Importante: salvar como index.html para o GitHub Pages funcionar
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_processadas))

if __name__ == "__main__":
    gerar_painel()
