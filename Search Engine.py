import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API (GitHub Secrets)
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            print("✅ Perfil carregado com sucesso.")
            return f.read()
    except FileNotFoundError:
        print("❌ ERRO: Perfil.txt não encontrado.")
        return ""

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    """Prompt otimizado para reconhecer competências transferíveis."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Candidato: Rafael Almeida. 
    Perfil: {perfil}
    
    Vaga encontrada:
    {descricao_vaga}
    
    INSTRUÇÕES PARA O MATCH:
    1. Rafael tem +15 anos de experiência e é especialista em Telecom, mas sua stack técnica é Python, BI e Meta Ads.
    2. Se a vaga pedir Python, Automação, Dashboards ou Gestão de Performance, considere um MATCH, mesmo que não seja no setor de Telecom.
    3. Seja flexível: se ele tem 60% das competências técnicas, aprove.
    
    RESPOSTA:
    - Se aprovado: 'APROVADO | [Nota]% | [Explique brevemente por que a experiência dele com KPIs e dados se aplica aqui]'
    - Se reprovado: 'REPROVADO'
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRO IA: {e}"

def buscar_e_gerar():
    perfil = carregar_perfil()
    if not perfil: return

    # Queries que deram resultado no seu log
    queries = [
        "Analista de BI",
        "Analista de Performance Marketing",
        "Analista Comercial Inteligência",
        "Desenvolvedor Python Automação",
        "Especialista em KPIs"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"🚀 Analisando {len(queries)} categorias de vagas...")

    for query in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": query,
                "hl": "pt-br",
                "gl": "br",
                "location": "Brazil",
                "api_key": SERP_API_KEY
            }
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])
            
            print(f"🔍 {query}: {len(results)} vagas para analisar.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    analise = avaliar_vaga_com_ia(perfil, v.get("description", ""))
                    
                    if "APROVADO" in analise.upper():
                        print(f"   ⭐ MATCH ENCONTRADO: {v.get('title')}")
                        vagas_finais.append({
                            "titulo": v.get("title"),
                            "empresa": v.get("company_name"),
                            "link": v.get("related_links", [{}])[0].get("link", "#"),
                            "local": v.get("location", "Brasil"),
                            "analise": analise.replace("APROVADO |", "").strip()
                        })
        except Exception as e:
            print(f"❌ Erro em '{query}': {e}")

    # Geração do HTML
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Jobs Finder IA | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-50 p-6">
        <div class="max-w-4xl mx-auto">
            <header class="flex justify-between items-center mb-12 border-b border-slate-800 pb-6">
                <div>
                    <h1 class="text-2xl font-bold text-blue-400">JOBS FINDER IA</h1>
                    <p class="text-slate-400 text-sm">Filtro de competências para Rafael Almeida</p>
                </div>
                <div class="text-right text-xs text-slate-500 uppercase">Sincronizado: {{ data }}</div>
            </header>

            <div class="grid gap-6">
                {% for vaga in vagas %}
                <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 hover:border-blue-500 transition">
                    <h2 class="text-lg font-bold">{{ vaga.titulo }}</h2>
                    <p class="text-blue-400 mb-4">{{ vaga.empresa }} • {{ vaga.local }}</p>
                    <div class="bg-black/30 p-4 rounded text-sm text-slate-300 italic mb-6">
                        {{ vaga.analise }}
                    </div>
                    <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 px-6 py-2 rounded-lg font-bold text-sm hover:bg-blue-500">Ver Vaga</a>
                </div>
                {% endfor %}
                
                {% if not vagas %}
                <p class="text-center text-slate-600 py-20">Nenhum match técnico encontrado para os critérios atuais.</p>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje))
    
    print(f"✅ Fim do processo. Vagas aprovadas: {len(vagas_finais)}")

if __name__ == "__main__":
    buscar_e_gerar()
