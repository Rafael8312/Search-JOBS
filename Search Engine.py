import os
import datetime
from serpapi import GoogleSearch
import google.generativeai as genai
from jinja2 import Template

# 1. Configurações de API
# No GitHub, ele pega dos Secrets. No PC, você pode definir como variável de ambiente ou substituir o texto.
SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuração do Gemini
genai.configure(api_key=GEMINI_API_KEY)

def carregar_perfil():
    """Lê o arquivo de perfil do Rafael."""
    try:
        with open("Perfil.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Erro ao ler Perfil.txt: {e}")
        return ""

def avaliar_vaga_com_ia(perfil, titulo, empresa, descricao):
    """O coração do sistema: IA decide se a vaga serve para você."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Candidato: Rafael Almeida.
    Especialidade: BI, Python, Automação, Telecom, Performance Marketing (Meta Ads).
    Perfil Completo: {perfil}

    Vaga: {titulo} na empresa {empresa}.
    Descrição: {descricao[:3000]}

    Tarefa:
    1. Verifique se a vaga envolve Dados, BI, Automação, Python ou Gestão Comercial.
    2. Rafael tem 15 anos de experiência. Se a vaga for para Analista Pleno, Sênior ou Especialista, o match é alto.
    3. Se houver ao menos 40% de compatibilidade técnica, aprove.

    Resposta (Siga o modelo):
    - APROVADO | [Nota]% | [Motivo curto]
    - REPROVADO | [Motivo curto]
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "REPROVADO | Erro na conexão com IA"

def buscar_e_gerar():
    perfil = carregar_perfil()
    if not perfil:
        return

    # Termos de busca diretos e potentes
    queries = [
        "Analista de BI",
        "Performance Marketing",
        "Python Developer",
        "Inteligência Comercial",
        "Especialista em Automação"
    ]
    
    vagas_finais = []
    vagas_vistas = set()

    print(f"🚀 Iniciando busca ampliada para {len(queries)} termos...")

    for query in queries:
        try:
            # PARÂMETROS SIMPLIFICADOS (Evita o erro de 0 resultados)
            params = {
                "engine": "google_jobs",
                "q": query,
                "api_key": SERP_API_KEY
            }
            
            search = GoogleSearch(params)
            results_dict = search.get_dict()
            
            if "error" in results_dict:
                print(f"❌ Erro na SerpApi ({query}): {results_dict['error']}")
                continue

            results = results_dict.get("jobs_results", [])
            print(f"🔍 {query}: {len(results)} vagas encontradas.")

            for v in results:
                job_id = v.get("job_id")
                if job_id and job_id not in vagas_vistas:
                    vagas_vistas.add(job_id)
                    
                    titulo = v.get('title')
                    empresa = v.get('company_name')
                    
                    # A IA faz o filtro fino
                    analise = avaliar_vaga_com_ia(perfil, titulo, empresa, v.get("description", ""))
                    
                    if "APROVADO" in analise.upper():
                        print(f"   ✅ MATCH: {titulo} na {empresa}")
                        vagas_finais.append({
                            "titulo": titulo,
                            "empresa": empresa,
                            "link": v.get("related_links", [{}])[0].get("link", "#"),
                            "analise": analise.replace("APROVADO |", "").strip()
                        })
                    else:
                        print(f"   ❌ REPROVADA: {titulo} (Baixo match)")

        except Exception as e:
            print(f"❌ Falha crítica na busca '{query}': {e}")

    # Geração do Painel HTML
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Radar de Vagas IA</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-400 mb-2">Radar de Vagas | Rafael Almeida</h1>
            <p class="text-slate-400 mb-10 text-sm">Atualizado em: {{ data }}</p>
            
            <div class="space-y-6">
                {% for vaga in vagas %}
                <div class="bg-slate-800 p-6 rounded-xl border-l-4 border-blue-500 shadow-xl">
                    <h2 class="text-xl font-bold">{{ vaga.titulo }}</h2>
                    <p class="text-blue-300 mb-4">{{ vaga.empresa }}</p>
                    <div class="bg-black/20 p-4 rounded text-slate-300 italic text-sm mb-6">
                        {{ vaga.analise }}
                    </div>
                    <a href="{{ vaga.link }}" target="_blank" class="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg font-bold transition">Candidatar-se</a>
                </div>
                {% endfor %}
                
                {% if not vagas %}
                <div class="text-center py-20 border-2 border-dashed border-slate-700 rounded-xl">
                    <p class="text-slate-500">Nenhuma vaga aprovada pela IA hoje. Verifique os logs.</p>
                </div>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("Painel.html", "w", encoding="utf-8") as f:
        f.write(Template(html_template).render(vagas=vagas_finais, data=data_hoje))
    
    print(f"✅ Processo finalizado. Painel atualizado com {len(vagas_finais)} vagas.")

if __name__ == "__main__":
    buscar_e_gerar()
