import os
import datetime
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
    
    # Prompt focado em extração de competências e cálculo de %
    prompt = f"""
    Candidato: Rafael Almeida.
    Perfil: {perfil}
    
    Vaga: {titulo} na {empresa}.
    Descrição: {descricao[:3000]}

    TAREFA:
    1. Liste as 5 principais competências técnicas/ferramentas exigidas pela vaga.
    2. Verifique quais dessas o Rafael possui.
    3. Calcule o percentual exato de compatibilidade (ex: possui 2 de 5 = 40%).
    4. Seja objetivo.

    SAÍDA OBRIGATÓRIA (Siga exatamente este formato):
    MATCH: [VALOR NUMÉRICO]% | MOTIVO: [Breve explicação das competências encontradas]
    """
    try:
        response = model.generate_content(prompt)
        res_text = response.text
        # Extrai o número do percentual para facilitar a ordenação posterior
        import re
        match_num = re.search(r"(\d+)%", res_text)
        percentual = int(match_num.group(1)) if match_num else 0
        return percentual, res_text
    except:
        return 0, "MATCH: 0% | Erro na análise"

def buscar_e_gerar():
    perfil = carregar_perfil()
    # Queries globais e técnicas
    queries = [
        "Business Intelligence Analyst",
        "Python Automation Engineer",
        "Performance Marketing Specialist",
        "Data Analyst SQL Python",
        "Meta Ads Specialist"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"🚀 Iniciando varredura global por competências...")

    for query in queries:
        try:
            # Sem restrição de 'gl' ou 'location' para ser global
            params = {
                "engine": "google_jobs",
                "q": query,
                "api_key": SERP_API_KEY
            }
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])
            print(f"🔍 {query}: {len(results)} encontradas.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    titulo = v.get('title')
                    empresa = v.get('company_name')
                    # Obtém a nota numérica e o texto da análise
                    nota, analise_texto = avaliar_vaga_com_ia(perfil, titulo, empresa, v.get("description", ""))
                    
                    # Trazemos TODAS as vagas que a IA conseguiu processar (independente da nota)
                    vagas_finais.append({
                        "titulo": titulo,
                        "empresa": empresa,
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "local": v.get("location", "Não especificado"),
                        "match_score": nota,
                        "analise": analise_texto
                    })
                    print(f"   📊 Analisada: {titulo} - {nota}%")
        except Exception as e:
            print(f"❌ Falha: {e}")

    # Geração do HTML com Filtro Dinâmico (JavaScript)
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Painel Global de Competências</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0f172a; color: #f8fafc; }
            .vaga-card { transition: 0.3s; }
        </style>
    </head>
    <body class="p-6 md:p-12">
        <header class="max-w-6xl mx-auto mb-10 border-b border-slate-700 pb-6 flex justify-between items-end">
            <div>
                <h1 class="text-3xl font-bold text-blue-400">Radar Global de Competências</h1>
                <p class="text-slate-400">Rafael Almeida | BI, Python & Performance</p>
            </div>
            <div class="text-right">
                <label class="text-xs uppercase text-slate-500 block mb-2 font-bold">Ordenar resultados:</label>
                <select id="sortOrder" onchange="ordenarVagas()" class="bg-slate-800 text-white px-4 py-2 rounded-lg outline-none border border-slate-600">
                    <option value="desc">Maior Match (%)</option>
                    <option value="asc">Menor Match (%)</option>
                </select>
            </div>
        </header>

        <main id="vagasContainer" class="max-w-6xl mx-auto grid gap-6">
            {% for vaga in vagas %}
            <div class="vaga-card bg-slate-800 p-6 rounded-2xl border border-slate-700 flex flex-col md:flex-row justify-between items-start md:items-center gap-4" data-score="{{ vaga.match_score }}">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                        <span class="bg-blue-900 text-blue-300 px-3 py-1 rounded-full text-xs font-bold">{{ vaga.match_score }}% MATCH</span>
                        <h2 class="text-xl font-bold">{{ vaga.titulo }}</h2>
                    </div>
                    <p class="text-slate-400 text-sm mb-4">{{ vaga.empresa }} • {{ vaga.local }}</p>
                    <p class="text-slate-300 text-xs italic bg-slate-900/50 p-3 rounded-lg">{{ vaga.analise }}</p>
                </div>
                <div class="w-full md:w-auto">
                    <a href="{{ vaga.link }}" target="_blank" class="block text-center bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold transition shadow-lg shadow-blue-900/20">Candidatar-se</a>
                </div>
            </div>
            {% endfor %}
        </main>

        <script>
            function ordenarVagas() {
                const container = document.getElementById('vagasContainer');
                const order = document.getElementById('sortOrder').value;
                const vagas = Array.from(container.getElementsByClassName('vaga-card'));

                vagas.sort((a, b) => {
                    const scoreA = parseInt(a.getAttribute('data-score'));
                    const scoreB = parseInt(b.getAttribute('data-score'));
                    return order === 'desc' ? scoreB - scoreA : scoreA - scoreB;
                });

                vagas.forEach(vaga => container.appendChild(vaga));
            }
            // Inicia ordenado por maior score
            window.onload = ordenarVagas;
        </script>
    </body>
    </html>
    """
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje))
    
    print(f"✅ Processo finalizado. {len(vagas_finais)} vagas no painel.")

if __name__ == "__main__":
    buscar_e_gerar()
