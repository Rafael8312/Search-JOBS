import os
import json
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# APIs
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except: return "Perfil de Rafael Almeida: Especialista em BI, Python, Meta Ads e SQL."

def analisar_vaga_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil[:1500]}
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Responda APENAS um JSON:
    {{
      "match": (0 a 100),
      "localizacao": ("Brasil" ou "Exterior"),
      "modalidade": ("Remoto" ou "Presencial"),
      "insight": (texto curto)
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Extrai apenas o que está entre chaves {}
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_str)
        return data['match'], data['localizacao'], data['modalidade'], data['insight']
    except:
        return 50, "Exterior", "Presencial", "Análise genérica - Erro de processamento."

def executar():
    perfil = carregar_perfil()
    # Aumentamos a precisão das buscas no Brasil
    queries = [
        {"q": "Analista de BI", "loc": "Brazil"},
        {"q": "Especialista Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation Remote", "loc": None}
    ]
    
    vagas_final = []
    vistos = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY}
            if item["loc"]: params.update({"location": "Brazil", "gl": "br", "hl": "pt-br"})
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                jid = v.get("job_id")
                if jid and jid not in vistos:
                    vistos.add(jid)
                    # Pegamos o link real da vaga aqui
                    link_real = v.get("related_links", [{}])[0].get("link", v.get("apply_link", "#"))
                    
                    m, p, r, ins = analisar_vaga_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_final.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": link_real,
                        "cidade": v.get("location", "Não informado"),
                        "match": m, "pais": p, "regime": r, "motivo": ins
                    })
        except: continue

    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>IA Jobs Finder | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-[#0b0e14] text-slate-200 p-4 md:p-10 font-sans">
        <div class="max-w-4xl mx-auto">
            <header class="text-center mb-12">
                <h1 class="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">JOBS FINDER IA</h1>
                <p class="text-slate-500 mt-2">Filtros Inteligentes para Rafael Almeida</p>
                
                <div class="mt-8 flex flex-wrap justify-center gap-3">
                    <button onclick="setPais('todos')" id="p-todos" class="btn-p bg-slate-800 px-6 py-2 rounded-xl font-bold border border-slate-700">Todos</button>
                    <button onclick="setPais('Brasil')" id="p-Brasil" class="btn-p bg-slate-800 px-6 py-2 rounded-xl font-bold border border-slate-700">🇧🇷 Brasil</button>
                    <button onclick="setPais('Exterior')" id="p-Exterior" class="btn-p bg-slate-800 px-6 py-2 rounded-xl font-bold border border-slate-700">🌍 Exterior</button>
                    <div class="flex items-center gap-2 ml-4 bg-slate-900 px-4 py-2 rounded-xl border border-slate-800">
                        <input type="checkbox" id="remotoCheck" onchange="aplicar()" class="w-4 h-4">
                        <label for="remotoCheck" class="text-sm font-bold text-purple-400">APENAS REMOTO</label>
                    </div>
                </div>
            </header>

            <div id="grid-vagas" class="space-y-4">
                {% for v in vagas %}
                <div class="vaga-card bg-[#161b26] p-6 rounded-3xl border border-slate-800 transition hover:border-blue-500" 
                     data-pais="{{v.pais}}" data-regime="{{v.regime}}" data-score="{{v.match}}">
                    <div class="flex flex-col md:row justify-between gap-4">
                        <div class="flex-1">
                            <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">{{v.pais}} • {{v.regime}}</span>
                            <h2 class="text-xl font-bold text-white mt-1">{{v.titulo}}</h2>
                            <p class="text-slate-400 text-sm mb-4">{{v.empresa}} ({{v.cidade}})</p>
                            <p class="text-slate-300 text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-emerald-500">{{v.motivo}}</p>
                        </div>
                        <div class="text-center md:text-right min-w-[120px]">
                            <div class="text-4xl font-black text-emerald-400">{{v.match}}%</div>
                            <div class="text-[10px] text-slate-500 uppercase mb-4">Match</div>
                            <a href="{{v.link}}" target="_blank" class="block bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-900/20">CANDIDATAR</a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            let paisAtual = 'todos';
            function setPais(p) {
                paisAtual = p;
                document.querySelectorAll('.btn-p').forEach(b => b.classList.replace('bg-blue-600', 'bg-slate-800'));
                document.getElementById('p-' + p).classList.replace('bg-slate-800', 'bg-blue-600');
                aplicar();
            }
            function aplicar() {
                const isRemoto = document.getElementById('remotoCheck').checked;
                document.querySelectorAll('.vaga-card').forEach(card => {
                    const matchPais = paisAtual === 'todos' || card.dataset.pais === paisAtual;
                    const matchRegime = !isRemoto || card.dataset.regime === 'Remoto';
                    card.style.display = (matchPais && matchRegime) ? 'block' : 'none';
                });
            }
            window.onload = () => {
                setPais('todos');
                const g = document.getElementById('grid-vagas');
                const cards = Array.from(g.children);
                cards.sort((a,b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => g.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_final))

if __name__ == "__main__":
    executar()
