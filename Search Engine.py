import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API (GitHub Secrets)
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AJUSTE ESTES DADOS PARA O SEU REPOSITÓRIO
GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    """Carrega o perfil limpo do arquivo Perfil.txt."""
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            print("✅ Perfil carregado com sucesso.")
            return f.read()
    except FileNotFoundError:
        print("❌ ERRO: Perfil.txt não encontrado.")
        return ""

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    """O Gemini avalia a vaga com nota de corte de 70%."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Candidato: Rafael de Almeida Soares.
    Perfil: {perfil}
    Vaga: {descricao_vaga}
    
    TAREFA:
    1. Avalie a compatibilidade (0-100%).
    2. Foque em: Python, BI, Meta Ads e Experiência Comercial/Telecom.
    3. Se o match for >= 70%, responda: 'APROVADO | [Nota]% | [Resumo curto]'.
    4. Caso contrário, responda: 'REPROVADO'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRO IA: {e}"

def buscar_e_gerar():
    perfil = carregar_perfil()
    if not perfil: return

    # 2. Queries otimizadas (Termos que o Google Jobs entende melhor no BR)
    queries = [
        "Analista de BI",
        "Analista de Performance Marketing",
        "Analista Comercial Inteligência",
        "Desenvolvedor Python Automação",
        "Especialista em KPIs"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"🚀 Iniciando busca para {len(queries)} termos no Brasil...")

    for query in queries:
        try:
            # PARÂMETROS CRÍTICOS PARA FUNCIONAR NO BRASIL
            params = {
                "engine": "google_jobs",
                "q": query,
                "hl": "pt-br",     # Idioma Português
                "gl": "br",        # País Brasil
                "location": "Brazil",
                "api_key": SERP_API_KEY
            }
            
            search = GoogleSearch(params)
            results = search.get_dict().get("jobs_results", [])
            
            print(f"🔍 Busca '{query}': {len(results)} vagas encontradas.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    # Análise da IA
                    analise = avaliar_vaga_com_ia(perfil, v.get("description", ""))
                    
                    if "APROVADO" in analise.upper():
                        print(f"   ⭐ MATCH: {v.get('title')} ({v.get('company_name')})")
                        vagas_finais.append({
                            "titulo": v.get("title"),
                            "empresa": v.get("company_name"),
                            "link": v.get("related_links", [{}])[0].get("link", "#"),
                            "local": v.get("location", "Remoto/Brasil"),
                            "analise": analise.replace("APROVADO |", "").strip()
                        })
        except Exception as e:
            print(f"❌ Erro na busca '{query}': {e}")

    # 3. Gerar o HTML atualizado
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    link_github = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions"

    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>AI Job Matcher | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; }
            .job-card { background: #1e293b; border-left: 4px solid #38bdf8; }
            .btn-update { border: 1px solid #38bdf8; color: #38bdf8; }
        </style>
    </head>
    <body class="p-6 md:p-12">
        <header class="max-w-5xl mx-auto mb-10 flex flex-col md:flex-row justify-between items-center gap-4">
            <div>
                <h1 class="text-3xl font-bold italic">JOBS <span class="text-blue-400">FINDER IA</span></h1>
                <p class="text-slate-400">Match 70%+ para Rafael Almeida</p>
            </div>
            <div class="text-center md:text-right">
                <a href="{{ link_github }}" target="_blank" class="btn-update px-6 py-2 rounded-full text-xs font-bold uppercase tracking-widest hover:bg-blue-400 hover:text-slate-900 transition">
                    🔄 Novo Start Manual
                </a>
                <p class="text-[10px] text-slate-500 mt-2">Sincronizado: {{ data }}</p>
            </div>
        </header>

        <main class="max-w-5xl mx-auto grid gap-6">
            {% for vaga in vagas %}
            <div class="job-card p-6 rounded-2xl shadow-2xl">
                <h2 class="text-xl font-bold text-white uppercase">{{ vaga.titulo }}</h2>
                <p class="text-blue-400 font-semibold mb-3">{{ vaga.empresa }} • {{ vaga.local }}</p>
                <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 text-slate-300 text-sm italic">
                    {{ vaga.analise }}
                </div>
                <div class="mt-6">
                    <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold text-sm inline-block">
                        Candidatar-me
                    </a>
                </div>
            </div>
            {% endfor %}
            
            {% if not vagas %}
            <div class="text-center py-20 border-2 border-dashed border-slate-800 rounded-3xl">
                <p class="text-slate-500">Nenhuma vaga com match relevante encontrada hoje.</p>
            </div>
            {% endif %}
        </main>
    </body>
    </html>
    """
    
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje, link_github=link_github))
    
    print(f"✅ Painel atualizado com {len(vagas_finais)} vagas.")

if __name__ == "__main__":
    buscar_e_gerar()
