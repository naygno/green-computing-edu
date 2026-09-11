import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# Configurações de Ambiente
SHORT_IO_API_KEY = os.environ.get("SHORT_IO_API_KEY")
SHORT_IO_DOMAIN_ID = os.environ.get("DOMAIN_ID") # Usamos o Domain ID agora
SHORT_IO_LINK_ID = os.environ.get("SHORT_IO_LINK_ID") # Mantemos o ID do link para filtrar

if not SHORT_IO_API_KEY or not SHORT_IO_DOMAIN_ID or not SHORT_IO_LINK_ID:
    raise ValueError("Variáveis de ambiente ausentes. Verifique: SHORT_IO_API_KEY, DOMAIN_ID e SHORT_IO_LINK_ID.")

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry():
    """
    Busca estatísticas do DOMÍNIO e filtra pelo link específico.
    O endpoint /statistics/link/{id} não existe publicamente na Short.io.
    """
    headers = {
        "Authorization": SHORT_IO_API_KEY,
        "Accept": "application/json"
    }
    
    # Endpoint CORRETO: Estatísticas do Domínio Inteiro
    url_stats = f"https://api.short.io/api/statistics/domain/{SHORT_IO_DOMAIN_ID}"
    
    print(f"📡 Buscando estatísticas do domínio {SHORT_IO_DOMAIN_ID}...")
    
    try:
        response = requests.get(url_stats, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # A resposta vem como uma lista de objetos 'clicks' por link
        # Estrutura típica: [{'idString': 'link_...', 'totalClicks': 123}, ...]
        links_stats = data.get('clicks', [])
        
        if not isinstance(links_stats, list):
            print(f"⚠️ Formato inesperado da API. Retorno: {data}")
            return 0

        total_clicks = 0
        found = False
        
        for item in links_stats:
            # Compara o idString retornado com o nosso ID alvo
            if item.get('idString') == SHORT_IO_LINK_ID:
                total_clicks = item.get('totalClicks', 0)
                found = True
                break
        
        if not found:
            print(f"⚠️ Link {SHORT_IO_LINK_ID} não encontrado na lista de estatísticas do domínio.")
            # Fallback: se não achar, retorna 0 mas não falha o script
            return 0
            
        print(f"✅ Cliques encontrados para {SHORT_IO_LINK_ID}: {total_clicks}")
        return int(total_clicks)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição à API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Resposta da API: {e.response.text}")
        raise

def update_history_and_chart(clicks):
    tz_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%Y-%m-%d")
    
    os.makedirs("assets", exist_ok=True)

    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        df["data"] = df["data"].astype(str)
    else:
        df = pd.DataFrame(columns=["data", "cliques"])
        
    if hoje in df["data"].values:
        df.loc[df["data"] == hoje, "cliques"] = clicks
    else:
        novo_registro = pd.DataFrame([{"data": hoje, "cliques": clicks}])
        df = pd.concat([df, novo_registro], ignore_index=True)
        
    df.to_csv(CSV_PATH, index=False)
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))
    
    if not df.empty:
        ax.plot(df["data"], df["cliques"], marker='o', color='#3fb950', linewidth=2, markersize=8)
        ax.fill_between(df["data"], df["cliques"], color='#3fb950', alpha=0.2)
    
    ax.set_title("Evolução de Adesão à Campanha (Cliques Validados)", fontsize=14, pad=15)
    ax.set_xlabel("Data", fontsize=12)
    ax.set_ylabel("Total de Cliques", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig(CHART_PATH, dpi=300, transparent=True)
    plt.close()

def update_readme(clicks):
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        print("README.md não encontrado.")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = re.sub(
        r"<!-- CLICKS_START -->.*?<!-- CLICKS_END -->",
        f"<!-- CLICKS_START -->**{clicks}**<!-- CLICKS_END -->",
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r"<!-- DATE_START -->.*?<!-- DATE_END -->",
        f"<!-- DATE_START -->(Atualizado em {agora})<!-- DATE_END -->",
        content,
        flags=re.DOTALL
    )
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    total_clicks = get_telemetry()
    print(f"Total de cliques obtidos: {total_clicks}")
    update_history_and_chart(total_clicks)
    update_readme(total_clicks)
    print("Telemetria atualizada com sucesso!")