import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# Configurações de API
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AJUSTE ESTAS DUAS LINHAS COM SEUS DADOS REAIS
GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    with open("Perfil.txt", "r", encoding="utf-8") as f:
        return f.read()

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Analise se este perfil tem +70% de match com a vaga. Perfil: {perfil} Vaga: {descricao_vaga}. Responda 'APROVADO | [Nota]% | [Resumo]' ou 'REPROVADO'."
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "ERRO"

def buscar_e_gerar():
    perfil = carregar_perfil()
    queries = ["Analista Business Intelligence", "Analista de Performance Meta Ads", "Automação Python"]
    vagas_finais = []
    vagas_vistas = set()

    for query in queries:
        search = GoogleSearch({"engine": "google_jobs", "q": query, "api_key": SERP_API_KEY})
        results = search.get_dict().get("jobs_results", [])
        for v in results:
            if v.get("job_id") not in vagas_vistas:
                vagas_vistas.add(v.get("job_id"))
                analise = avaliar_vaga_com_ia(perfil, v.get("description", ""))
                if "APROVADO" in analise.upper():
                    vagas_finais.append({
                        "titulo": v.get("title"),
                        "empresa": v.get("company_name"),
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "analise": analise.replace("APROVADO |", "").strip()
                    })

    # Template com o Botão de Atualizar
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    link_github = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions"

    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>AI Job Matcher | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white p-10">
        <header class="max-w-5xl mx-auto mb-10 flex justify-between items-center">
            <div>
                <h1 class="text-3xl font-bold">Minhas Vagas <span class="text-blue-400">80% Match</span></h1>
                <p class="text-slate-400">Última atualização: {{ data }}</p>
            </div>
            <a href="{{ link_github }}" target="_blank" class="bg-transparent border border-blue-400 text-blue-400 px-4 py-2 rounded-lg hover:bg-blue-400 hover:text-slate-900 transition font-bold">
                🔄 Atualizar Vagas (Start Manual)
            </a>
        </header>
        <main class="max-w-5xl mx-auto grid gap-6">
            {% for vaga in vagas %}
            <div class="bg-slate-800 p-6 rounded-xl border-l-4 border-blue-500">
                <h2 class="text-xl font-bold">{{ vaga.titulo }}</h2>
                <p class="text-blue-300">{{ vaga.empresa }}</p>
                <p class="mt-4 text-slate-300 text-sm italic">{{ vaga.analise }}</p>
                <a href="{{ vaga.link }}" target="_blank" class="mt-4 inline-block bg-blue-600 px-4 py-2 rounded-lg font-bold">Ver Vaga</a>
            </div>
            {% endfor %}
        </main>
    </body>
    </html>
    """
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje, link_github=link_github))

if __name__ == "__main__":
    buscar_e_gerar()

