import os
import re
import json
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
    except: return "Perfil não carregado."

def analisar_vaga(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Forçamos o formato JSON para evitar que a IA "converse" e quebre o código
    prompt = f"""
    Analise a vaga para o candidato Rafael Almeida (Perfil: {perfil[:1500]}).
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Responda APENAS um JSON com:
    {{
      "match": (0 a 100 baseado em competências),
      "pais": ("Brasil" ou "Exterior"),
      "regime": ("Remoto" ou "Presencial"),
      "motivo": (texto curto)
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza para garantir que pegamos apenas o JSON
        txt = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(txt)
        return data['match'], data['pais'], data['regime'], data['motivo']
    except:
        return 0, "Exterior", "Presencial", "Erro na análise técnica."

def executar():
    perfil = carregar_perfil()
    queries = [
        {"q": "Analista de BI", "loc": "Brazil"},
        {"q": "Performance Marketing Meta Ads", "loc": "Brazil"},
        {"q": "Python Automation", "loc": None}
    ]
    
    lista_vagas = []
    vistos = set()

    for item in queries:
        try:
            params = {"engine": "google_jobs", "q": item["q"], "api_key": SERP_API_KEY}
            if item["loc"]: params.update({"location": "Brazil", "gl": "br"})
            
            search = GoogleSearch(params)
            for v in search.get_dict().get("jobs_results", []):
                id_vaga = v.get("job_id")
                if id_vaga and id_vaga not in vistos:
                    vistos.add(id_vaga)
                    m, p, r, mot = analisar_vaga(perfil, v.get('title'), v.get('company_name'), v.get("description", ""))
                    
                    lista_vagas.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local": v.get("location", "N/D"),
                        "score": m, "pais": p, "regime": r, "analise": mot
                    })
        except: continue

    # HTML com filtros que REALMENTE funcionam
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>IA Job Matcher | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-200 p-6">
        <div class="max-w-4xl mx-auto text-center mb-10">
            <h1 class="text-4xl font-black text-blue-400">JOB INTELLIGENCE</h1>
            <div class="mt-6 flex justify-center gap-4">
                <button onclick="filtrar('todos')" class="bg-slate-800 px-4 py-2 rounded">Todos</button>
                <button onclick="filtrar('Brasil')" class="bg-green-900 px-4 py-2 rounded">🇧🇷 Brasil</button>
                <button onclick="filtrar('Exterior')" class="bg-blue-900 px-4 py-2 rounded">🌍 Exterior</button>
                <label class="flex items-center gap-2 ml-4"><input type="checkbox" id="remoto" onchange="filtrar()"> Apenas Remoto</label>
            </div>
        </div>

        <div id="vagas" class="grid gap-4">
            {% for v in vagas %}
            <div class="vaga bg-slate-900 p-6 rounded-xl border border-slate-800" data-pais="{{v.pais}}" data-regime="{{v.regime}}" data-score="{{v.score}}">
                <div class="flex justify-between items-start">
                    <div>
                        <span class="text-xs font-bold text-blue-400 uppercase">{{v.pais}} | {{v.regime}}</span>
                        <h2 class="text-xl font-bold mt-1">{{v.titulo}}</h2>
                        <p class="text-slate-500 text-sm">{{v.empresa}} ({{v.local}})</p>
                    </div>
                    <div class="text-3xl font-black text-emerald-400">{{v.score}}%</div>
                </div>
                <p class="mt-4 text-sm text-slate-400 italic border-l-2 border-slate-700 pl-4">{{v.analise}}</p>
                <a href="{{v.link}}" target="_blank" class="mt-4 inline-block bg-blue-600 px-6 py-2 rounded font-bold text-sm">Ver Vaga</a>
            </div>
            {% endfor %}
        </div>

        <script>
            let paisFiltro = 'todos';
            function filtrar(p) {
                if(p) paisFiltro = p;
                const remoto = document.getElementById('remoto').checked;
                document.querySelectorAll('.vaga').forEach(v => {
                    const matchPais = paisFiltro === 'todos' || v.dataset.pais === paisFiltro;
                    const matchRemoto = !remoto || v.dataset.regime === 'Remoto';
                    v.style.display = (matchPais && matchRemoto) ? 'block' : 'none';
                });
            }
            window.onload = () => {
                const list = Array.from(document.querySelectorAll('.vaga'));
                list.sort((a,b) => b.dataset.score - a.dataset.score);
                list.forEach(v => document.getElementById('vagas').appendChild(v));
            };
        </script>
    </body>
    </html>
    """
    # MUDANÇA CRÍTICA: O arquivo deve se chamar index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=lista_vagas))

if __name__ == "__main__":
    executar()
