import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API (Essas variáveis devem estar no GitHub Secrets)
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Substitua com o seu usuário e nome do repositório para o botão de atalho funcionar
GITHUB_USER = "SEU_USUARIO"
GITHUB_REPO = "SEU_REPOSITORIO"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    """Lê o arquivo de perfil anexado para servir de base para a IA."""
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Perfil não encontrado."

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    """Usa o Gemini para comparar o perfil com a vaga e validar os 80% de match."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Analise o perfil do candidato Rafael de Almeida Soares em relação à vaga abaixo.
    
    PERFIL:
    {perfil}
    
    VAGA:
    {descricao_vaga}
    
    REGRAS DE RESPOSTA:
    1. Calcule a aderência técnica e comportamental (0 a 100%).
    2. Se o match for IGUAL ou SUPERIOR a 80%, responda estritamente: 'APROVADO | [Nota]% | [Breve resumo do porquê do match]'.
    3. Se for inferior a 80%, responda apenas 'REPROVADO'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRO NA ANÁLISE: {e}"

def buscar_e_gerar():
    perfil = carregar_perfil()
    
    # Termos de busca baseados no seu currículo (BI, Performance e Automação)
    queries = [
        "Analista Business Intelligence Pleno",
        "Analista de Performance Meta Ads",
        "Inteligência Comercial Automação Python",
        "Analista de Planejamento Comercial"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print("Iniciando varredura de vagas...")

    for query in queries:
        try:
            search = GoogleSearch({
                "engine": "google_jobs",
                "q": f"{query} remoto",
                "hl": "pt",
                "api_key": SERP_API_KEY
            })
            results = search.get_dict().get("jobs_results", [])

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    analise = avaliar_vaga_com_ia(perfil, v.get("description", ""))
                    
                    if "APROVADO" in analise.upper():
                        vagas_finais.append({
                            "titulo": v.get("title"),
                            "empresa": v.get("company_name"),
                            "link": v.get("related_links", [{}])[0].get("link", "#"),
                            "local": v.get("location", "Remoto/Brasil"),
                            "analise": analise.replace("APROVADO |", "").strip()
                        })
        except Exception as e:
            print(f"Erro na busca para '{query}': {e}")

    # 2. Template HTML com Visual Moderno e Botão de Atalho
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    link_actions = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions"

    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Job Matcher | Rafael Almeida</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; }
            .job-card { background: #1e293b; border-left: 4px solid #38bdf8; transition: 0.3s; }
            .job-card:hover { transform: scale(1.01); border-color: #818cf8; }
            .btn-start { border: 1px solid #38bdf8; color: #38bdf8; transition: 0.3s; }
            .btn-start:hover { background: #38bdf8; color: #0f172a; }
        </style>
    </head>
    <body class="p-4 md:p-12">
        <header class="max-w-5xl mx-auto mb-10 flex flex-col md:flex-row justify-between items-center gap-6">
            <div>
                <h1 class="text-3xl font-bold">Vagas <span class="text-blue-400 font-black">START 80%</span></h1>
                <p class="text-slate-400">Match inteligente para Rafael de Almeida Soares</p>
            </div>
            <div class="text-center md:text-right">
                <a href="{{ link_github }}" target="_blank" class="btn-start px-5 py-2 rounded-full text-sm font-bold inline-block mb-2">
                    🔄 Atualizar Vagas (GitHub Start)
                </a>
                <p class="text-[10px] text-slate-500 uppercase tracking-widest">Última busca: {{ data }}</p>
            </div>
        </header>

        <main class="max-w-5xl mx-auto grid gap-6">
            {% for vaga in vagas %}
            <div class="job-card p-6 rounded-2xl shadow-xl">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h2 class="text-xl font-bold text-white">{{ vaga.titulo }}</h2>
                        <p class="text-blue-400 font-medium">{{ vaga.empresa }} • {{ vaga.local }}</p>
                    </div>
                    <span class="bg-blue-900/40 text-blue-300 px-3 py-1 rounded-md text-xs font-bold border border-blue-500/30">
                        MATCH ATIVO
                    </span>
                </div>
                <p class="text-slate-300 text-sm leading-relaxed bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    {{ vaga.analise }}
                </p>
                <div class="mt-6">
                    <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold text-sm transition block text-center md:inline-block">
                        Candidatar-se na Origem
                    </a>
                </div>
            </div>
            {% endfor %}
            
            {% if not vagas %}
            <div class="text-center py-20 border-2 border-dashed border-slate-800 rounded-3xl">
                <p class="text-slate-500">Nenhuma vaga com +80% encontrada. Tente um novo start manual mais tarde.</p>
            </div>
            {% endif %}
        </main>
    </body>
    </html>
    """
    
    # Geração do arquivo final
    tmpl = Template(html_template)
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(tmpl.render(vagas=vagas_finais, data=data_hoje, link_github=link_actions))
    
    print(f"Sucesso! Painel.html atualizado com {len(vagas_finais)} vagas.")

if __name__ == "__main__":
    buscar_e_gerar()
