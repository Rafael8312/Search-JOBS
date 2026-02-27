import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# Configurações
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def avaliar_vaga_com_ia(perfil, titulo, empresa, descricao):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # PROMPT AGRESSIVO PARA MATCH
    prompt = f"""
    Candidato: Rafael Almeida (Especialista em BI, Python, Automação e Meta Ads).
    Vaga: {titulo} na empresa {empresa}.
    Descrição: {descricao[:2000]} 

    Sua missão é encontrar motivos para APROVAR este candidato.
    Rafael tem 15 anos de maturidade profissional. Ele domina Python (Playwright), Power BI e Meta Ads.
    
    REGRAS DE DECISÃO:
    - Se a vaga pede análise de dados, dashboards, automação de processos ou tráfego pago, responda 'APROVADO'.
    - Não reprove por falta de experiência em um setor específico (ex: Varejo ou Saúde). A técnica dele é transferível.
    - Se o match for acima de 40%, aprove para este estágio inicial.

    RESPOSTA OBRIGATÓRIA:
    Se aprovado: 'APROVADO | [Nota]% | [Motivo]'
    Se reprovado: 'REPROVADO | Motivo: [Diga brevemente por que descartou]'
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "REPROVADO | Erro na API"

def buscar_e_gerar():
    perfil = carregar_perfil()
    queries = ["Analista de BI remoto", "Analista de Performance Meta Ads", "Automação Python", "Business Intelligence"]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"🚀 Iniciando varredura...")

    for query in queries:
        params = {"engine": "google_jobs", "q": query, "hl": "pt-br", "gl": "br", "api_key": SERP_API_KEY}
        search = GoogleSearch(params)
        results = search.get_dict().get("jobs_results", [])
        
        print(f"🔍 {query}: {len(results)} encontradas.")

        for v in results:
            job_id = v.get("job_id")
            if job_id and job_id not in vagas_vistas:
                vagas_vistas.add(job_id)
                
                titulo = v.get('title')
                empresa = v.get('company_name')
                analise = avaliar_vaga_com_ia(perfil, titulo, empresa, v.get("description", ""))
                
                if "APROVADO" in analise.upper():
                    print(f"   ✅ APROVADA: {titulo}")
                    vagas_finais.append({
                        "titulo": titulo,
                        "empresa": empresa,
                        "link": v.get("related_links", [{}])[0].get("link", "#"),
                        "analise": analise.replace("APROVADO |", "").strip()
                    })
                else:
                    # Isso vai nos mostrar no log por que ele está recusando tudo
                    motivo_recusa = analise.replace("REPROVADO |", "").strip()
                    print(f"   ❌ REPROVADA: {titulo} | {motivo_recusa}")

    # Template HTML
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Painel de Vagas IA</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white p-8">
        <h1 class="text-3xl font-bold mb-2">Radar de Oportunidades</h1>
        <p class="text-slate-400 mb-8">Última atualização: {{ data }}</p>
        <div class="grid gap-4">
            {% for vaga in vagas %}
            <div class="bg-slate-800 p-6 rounded-lg border-l-4 border-blue-500">
                <h2 class="text-xl font-bold">{{ vaga.titulo }}</h2>
                <p class="text-blue-400 mb-2">{{ vaga.empresa }}</p>
                <p class="text-slate-300 text-sm italic mb-4">{{ vaga.analise }}</p>
                <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 px-4 py-2 rounded font-bold">Ver Vaga</a>
            </div>
            {% endfor %}
            {% if not vagas %}
            <p class="text-slate-500">A IA ainda não encontrou vagas ideais hoje. Verifique os logs do GitHub para entender os motivos.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje))
    
    print(f"✅ Painel atualizado. Total aprovado: {len(vagas_finais)}")

if __name__ == "__main__":
    buscar_e_gerar()
