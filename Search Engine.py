import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

GITHUB_USER = "Rafael8312"
GITHUB_REPO = "Search-JOBS"

def carregar_perfil():
    with open("Perfil.txt", "r", encoding="utf-8") as f:
        return f.read()

def avaliar_vaga_com_ia(perfil, descricao_vaga):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Candidato: Rafael de Almeida Soares.
    Perfil: {perfil}
    Vaga: {descricao_vaga}
    
    TAREFA:
    1. Avalie a compatibilidade (0-100%).
    2. Considere que ele tem forte background em Telecom, BI e Automação Python.
    3. Se o match for >= 70%, responda: 'APROVADO | [Nota]% | [Explique o motivo do match em 10 palavras]'.
    4. Caso contrário, responda apenas 'REPROVADO'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "ERRO"

def buscar_e_gerar():
    perfil = carregar_perfil()
    # QUERIES MAIS AMPLAS PARA PEGAR MAIS RESULTADOS
    queries = [
        "Analista Comercial Pleno remoto",
        "Business Intelligence remoto",
        "Analista de Performance Marketing",
        "Supervisor de Vendas remoto",
        "Inteligência Comercial"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    for query in queries:
        # Buscando mais resultados (aumentado para num=20 se disponível)
        search = GoogleSearch({
            "engine": "google_jobs",
            "q": query,
            "hl": "pt",
            "gl": "br", 
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
                        "local": v.get("location", "Brasil (Remoto)"),
                        "analise": analise.replace("APROVADO |", "").strip()
                    })

    # Renderização (Mesmo layout, mas com o link correto)
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    link_github = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions"
    
    # ... (Abaixo segue o mesmo código de Template HTML que você já possui)
    # Certifique-se de manter a parte final que grava o Painel.html
