import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API (Devem estar nos Secrets do GitHub)
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AJUSTE ESTES DADOS
GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    """Lê o perfil atualizado e organizado."""
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            content = f.read()
            print("✅ Perfil carregado com sucesso.")
            return content
    except FileNotFoundError:
        print("❌ ERRO: Arquivo Perfil.txt não encontrado.")
        return ""

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    """Usa o Gemini para validar o match de 70%."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Analise o perfil do candidato Rafael Almeida em relação à vaga abaixo.
    
    PERFIL:
    {perfil}
    
    VAGA:
    {descricao_vaga}
    
    REGRAS:
    1. Avalie a compatibilidade técnica (Python, BI, Meta Ads) e de liderança (Telecom/Vendas).
    2. Se o match for IGUAL ou SUPERIOR a 70%, responda: 'APROVADO | [Nota]% | [Resumo curto do match]'.
    3. Se for inferior a 70%, responda apenas 'REPROVADO'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRO: {e}"

def buscar_e_gerar():
    perfil = carregar_perfil()
    if not perfil: return

    # 2. Busca focada em COMPETÊNCIAS e STACK TÉCNICA
    queries = [
        "Python automação remoto",
        "Analista de Performance Meta Ads",
        "Business Intelligence Power BI remoto",
        "Especialista em Automação de Processos",
        "Analista Comercial Inteligência de Dados",
        "Growth Marketing focado em dados"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"Iniciando busca para {len(queries)} termos...")

    for query in queries:
        try:
            search = GoogleSearch({
                "engine": "google_jobs",
                "q": query,
                "hl": "pt",
                "gl": "br", # Foco em vagas no Brasil
                "api_key": SERP_API_KEY
            })
            results = search.get_dict().get("jobs_results", [])
            print(f"🔍 Busca '{query}': {len(results)} vagas encontradas.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    # Análise pela IA
                    analise = avaliar_vaga_com_ia(perfil, v.get("description", ""))
                    
                    if "APROVADO" in analise.upper():
                        print(f"   ⭐ MATCH ENCONTRADO: {v.get('title')}")
                        vagas_finais.append({
                            "titulo": v.get("title"),
                            "empresa": v.get("company_name"),
                            "link": v.get("related_links", [{}])[0].get("link", "#"),
                            "local": v.get("location", "Remoto"),
                            "analise": analise.replace("APROVADO |", "").strip()
                        })
        except Exception as e:
            print(f"❌ Erro na busca '{query}': {e}")

    # 3. Geração do HTML com botão de atualização
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
            body { background-color: #0f172a; color: #f8fafc; }
            .job-card { background: #1e293b; border-left: 4px solid #38bdf8; transition: 0.3s; }
            .job-card:hover { transform: scale(1.01); border-color: #818cf8; }
            .btn-update { border: 1px solid #38bdf8; color: #38bdf8; transition: 0.3s; }
            .btn-update:hover { background: #38bdf8; color: #0f172a; }
        </style>
    </head>
    <body class="p-6 md:p-12">
        <header class="max-w-5xl mx-auto mb-12 flex flex-col md:row justify-between items-center gap-6">
            <div>
                <h1 class="text-3xl font-bold">Vagas <span class="text-blue-400">Match 70%+</span></h1>
                <p class="text-slate-400">Filtro inteligente para Rafael de Almeida Soares</p>
            </div>
            <div class="text-right">
                <a href="{{ link_github }}" target="_blank" class="btn-update px-5 py-2 rounded-full text-sm font-bold inline-block mb-2">
                    🔄 Atualizar Painel
                </a>
                <p class="text-[10px] text-slate-500 uppercase tracking-widest">Última Varredura: {{ data }}</p>
            </div>
        </header>

        <main class="max-w-5xl mx-auto grid gap-6">
            {% for vaga in vagas %}
            <div class="job-card p-6 rounded-2xl shadow-xl">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h2 class="text-xl font-bold text-white uppercase">{{ vaga.titulo }}</h2>
                        <p class="text-blue-400 font-medium">{{ vaga.empresa }} • {{ vaga.local }}</p>
                    </div>
                </div>
                <p class="text-slate-300 text-sm leading-relaxed bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
                    {{ vaga.analise }}
                </p>
                <div class="mt-6">
                    <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold text-sm transition block text-center md:inline-block">
                        Candidatar-se
                    </a>
                </div>
            </div>
            {% endfor %}
            
            {% if not vagas %}
            <div class="text-center py-20 border-2 border-dashed border-slate-800 rounded-3xl">
                <p class="text-slate-500 italic">Nenhum match de 70% encontrado nas buscas de hoje. Tente atualizar mais tarde.</p>
            </div>
            {% endif %}
        </main>
    </body>
    </html>
    """
    
    tmpl = Template(html_template)
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(tmpl.render(vagas=vagas_finais, data=data_hoje, link_github=link_actions))
    
    print(f"✅ Processo concluído. {len(vagas_finais)} vagas salvas no Painel.html.")

if __name__ == "__main__":
    buscar_e_gerar()
