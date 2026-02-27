import os
import json
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# Configurações de API
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    # Retorna um resumo caso o arquivo falhe, para garantir que o match nunca seja 0% por erro de leitura
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Rafael Almeida: Especialista em BI, Python, SQL e Performance Marketing."

def analisar_vaga_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # O prompt agora exige JSON puro. Se a IA falar qualquer coisa fora do JSON, o código limpa.
    prompt = f"""
    Analise a vaga para Rafael Almeida. Perfil: {perfil[:1500]}
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Responda APENAS um objeto JSON exatamente assim:
    {{
      "match": (número de 0 a 100),
      "pais": ("Brasil" ou "Exterior"),
      "regime": ("Remoto" ou "Presencial"),
      "motivo": (máximo 15 palavras)
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza robusta para pegar apenas o conteúdo entre as chaves {}
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data['match'], data['pais'], data['regime'], data['motivo']
        return 50, "Exterior", "Presencial", "Análise inconclusiva."
    except:
        return 0, "Exterior", "Presencial", "Erro técnico na análise."

def executar():
    perfil = carregar_perfil()
    queries = [
        {"q": "Analista de BI Brasil", "loc": "Brazil"},
        {"q": "Performance Marketing Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation Remote", "loc": None}
    ]
    
    vagas_list = []
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
                    # Busca o link real de candidatura
                    link = v.get("related_links", [{}])[0].get("link", v.get("apply_link", "#"))
                    
                    m, p, r, mot = analisar_vaga_ia(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    vagas_list.append({
                        "titulo": v.get('title'), "empresa": v.get('company_name'),
                        "link": link, "local": v.get("location", "N/D"),
                        "score": m, "pais": p, "regime": r, "analise": mot
                    })
        except: continue

    # HTML com filtros funcionando via JavaScript (sem recarregar)
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>IA Job Finder</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-[#0d1117] text-slate-300 p-4 md:p-10">
        <div class="max-w-4xl mx-auto">
            <header class="text-center mb-10">
                <h1 class="text-3xl font-black text-blue-500 uppercase tracking-tighter">Job Intelligence AI</h1>
                <div class="mt-6 flex flex-wrap justify-center gap-3">
                    <button onclick="fPais('todos')" id="p-todos" class="btn bg-blue-600 text-white px-5 py-2 rounded-lg font-bold">Todos</button>
                    <button onclick="fPais('Brasil')" id="p-Brasil" class="btn bg-slate-800 px-5 py-2 rounded-lg font-bold">Brasil</button>
                    <button onclick="fPais('Exterior')" id="p-Exterior" class="btn bg-slate-800 px-5 py-2 rounded-lg font-bold">Exterior</button>
                    <div class="flex items-center gap-2 bg-slate-900 px-4 py-2 rounded-lg border border-slate-700">
                        <input type="checkbox" id="remCheck" onchange="apply()" class="w-4 h-4">
                        <label for="remCheck" class="text-xs font-bold text-blue-400">APENAS REMOTO</label>
                    </div>
                </div>
            </header>

            <div id="job-list" class="space-y-4">
                {% for v in vagas %}
                <div class="job-card bg-[#161b22] p-6 rounded-2xl border border-slate-800" data-pais="{{v.pais}}" data-regime="{{v.regime}}" data-score="{{v.score}}">
                    <div class="flex justify-between items-start gap-4">
                        <div class="flex-1">
                            <span class="text-[10px] font-black text-blue-400 uppercase">{{v.pais}} • {{v.regime}}</span>
                            <h2 class="text-xl font-bold text-white mt-1">{{v.titulo}}</h2>
                            <p class="text-slate-500 text-sm">{{v.empresa}} ({{v.local}})</p>
                            <p class="mt-4 text-xs italic text-slate-400 border-l-2 border-blue-500 pl-3">{{v.analise}}</p>
                        </div>
                        <div class="text-center">
                            <div class="text-3xl font-black text-emerald-400">{{v.score}}%</div>
                            <a href="{{v.link}}" target="_blank" class="mt-4 block bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold py-2 px-4 rounded-lg">CANDIDATAR</a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        <script>
            let curPais = 'todos';
            function fPais(p) {
                curPais = p;
                document.querySelectorAll('.btn').forEach(b => b.classList.replace('bg-blue-600', 'bg-slate-800'));
                document.getElementById('p-'+p).classList.replace('bg-slate-800', 'bg-blue-600');
                apply();
            }
            function apply() {
                const isRem = document.getElementById('remCheck').checked;
                document.querySelectorAll('.job-card').forEach(c => {
                    const mP = curPais === 'todos' || c.dataset.pais === curPais;
                    const mR = !isRem || c.dataset.regime === 'Remoto';
                    c.style.display = (mP && mR) ? 'block' : 'none';
                });
            }
            window.onload = () => {
                const list = document.getElementById('job-list');
                const cards = Array.from(list.children);
                cards.sort((a,b) => b.dataset.score - a.dataset.score);
                cards.forEach(c => list.appendChild(c));
            }
        </script>
    </body>
    </html>
    """
    # CRÍTICO: O arquivo PRECISA se chamar index.html para o link principal funcionar
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_list))

if __name__ == "__main__":
    executar()
