import os
import json
import re
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

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
    prompt = f"""
    Candidato: Rafael Almeida. Perfil: {perfil[:1500]}
    Vaga: {titulo} na {empresa}. Descrição: {descricao[:1000]}
    
    Analise a compatibilidade entre o perfil do candidato e a vaga.
    Liste as competências da vaga e quais o candidato possui.
    Calcule o percentual: (competências que o candidato possui / total de competências da vaga) * 100.
    
    Responda APENAS um objeto JSON exatamente assim (sem texto extra, sem markdown):
    {{
      "match": <número inteiro de 0 a 100 representando o percentual de compatibilidade>,
      "regime": "<exatamente 'Remoto' ou 'Presencial'>",
      "insight": "<máximo 15 palavras sobre o match>"
    }}
    """
    try:
        response = model.generate_content(prompt)
        # CORREÇÃO 3: regex sem escapes desnecessários
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            match_val = int(data.get('match', 0))
            regime_val = data.get('regime', 'Presencial')
            insight_val = data.get('insight', 'Análise inconclusiva.')
            return match_val, regime_val, insight_val
        return 50, "Presencial", "Análise inconclusiva."
    except Exception as e:
        print(f"Erro IA: {e}")
        return 0, "Presencial", "Erro técnico na análise."

def executar():
    perfil = carregar_perfil()
    
    # CORREÇÃO 1: pais_label definido deterministicamente por query
    queries = [
        {"q": "Analista de BI", "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "Performance Marketing Meta Ads", "loc": "Brazil", "gl": "br", "hl": "pt-br", "pais_label": "Brasil"},
        {"q": "BI Analyst Remote", "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
        {"q": "Python Automation Specialist Remote", "loc": None, "gl": "us", "hl": "en", "pais_label": "Exterior"},
    ]
    
    vagas_list = []
    vistos = set()

    for item in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": item["q"],
                "api_key": SERP_API_KEY,
                "gl": item.get("gl", "us"),
                "hl": item.get("hl", "en"),
            }
            if item["loc"]:
                params["location"] = item["loc"]

            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                jid = v.get("job_id")
                if jid and jid not in vistos:
                    vistos.add(jid)

                    # CORREÇÃO 4: usar apply_options para link direto da vaga
                    apply_options = v.get("apply_options", [])
                    if apply_options:
                        link_vaga = apply_options[0].get("link", "#")
                    else:
                        # Fallback: related_links filtrado para excluir google.com
                        related = [
                            rl.get("link", "") 
                            for rl in v.get("related_links", [])
                            if "google.com" not in rl.get("link", "")
                        ]
                        link_vaga = related[0] if related else "#"

                    m, r, mot = analisar_vaga_ia(
                        perfil, v.get('title'), v.get('company_name'), v.get("description", "")
                    )

                    # CORREÇÃO 2: regime padronizado em português pelo prompt da IA
                    vagas_list.append({
                        "titulo": v.get('title'),
                        "empresa": v.get('company_name'),
                        "link": link_vaga,
                        "local": v.get("location", "N/D"),
                        "score": m,
                        "pais": item["pais_label"],  # CORREÇÃO 1: país fixo
                        "regime": r,
                        "analise": mot
                    })
        except Exception as e:
            print(f"Erro query: {e}")
            continue

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
                     data-pais="{{ v.pais }}" data-regime="{{ v.regime }}" data-score="{{ v.score }}">
                    <div class="flex flex-col md:flex-row justify-between gap-4">
                        <div class="flex-1">
                            <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest">{{ v.pais }} • {{ v.regime }}</span>
                            <h2 class="text-xl font-bold text-white mt-1">{{ v.titulo }}</h2>
                            <p class="text-slate-400 text-sm mb-4">{{ v.empresa }} ({{ v.local }})</p>
                            <p class="text-slate-300 text-xs italic bg-black/30 p-4 rounded-2xl border-l-4 border-emerald-500">{{ v.analise }}</p>
                        </div>
                        <div class="text-center md:text-right min-w-[120px]">
                            <div class="text-4xl font-black text-emerald-400">{{ v.score }}%</div>
                            <!-- CORREÇÃO 4: target="_blank" + rel para segurança -->
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
                // Reset todos os botões
                document.querySelectorAll('.btn').forEach(b => {
                    b.classList.remove('bg-blue-600');
                    b.classList.add('bg-slate-800');
                });
                // Ativa o botão clicado
                const btn = document.getElementById('p-' + p);
                if (btn) {
                    btn.classList.remove('bg-slate-800');
                    btn.classList.add('bg-blue-600');
                }
                apply();
            }

            function apply() {
                const rem = document.getElementById('remCheck').checked;
                document.querySelectorAll('.vaga-card').forEach(c => {
                    // CORREÇÃO 2: comparação com 'Remoto' (português, igual ao que a IA retorna)
                    const mP = paisF === 'todos' || c.dataset.pais === paisF;
                    const mR = !rem || c.dataset.regime === 'Remoto';
                    c.style.display = (mP && mR) ? 'block' : 'none';
                });
            }

            window.onload = () => {
                const g = document.getElementById('grid-vagas');
                const cards = Array.from(g.children);
                cards.sort((a, b) => Number(b.dataset.score) - Number(a.dataset.score));
                cards.forEach(c => g.appendChild(c));
                apply(); // Aplica o filtro padrão ao carregar
            }
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_list))

if __name__ == "__main__":
    executar()
