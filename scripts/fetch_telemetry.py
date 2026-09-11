import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# Configurações de Ambiente
SHORT_IO_API_KEY = os.environ.get("SHORT_IO_API_KEY")
if not SHORT_IO_API_KEY:
    raise ValueError("A variável SHORT_IO_API_KEY não foi encontrada. Verifique os Secrets do repositório.")
SHORT_IO_LINK_ID = os.environ.get("SHORT_IO_LINK_ID") # Usa o ID direto do link

# Validação de variáveis essenciais
if not SHORT_IO_API_KEY or not SHORT_IO_LINK_ID:
    raise ValueError("As variáveis SHORT_IO_API_KEY e SHORT_IO_LINK_ID são obrigatórias.")

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry():
    """Busca os cliques na API do Short.io usando o ID direto do link."""
    headers = {
        "Authorization": SHORT_IO_API_KEY,
        "Accept": "application/json"
    }
    
    # Endpoint direto de estatísticas pelo ID do link
    url_stats = f"https://api.short.io/api/statistics/link/{SHORT_IO_LINK_ID}"
    
    try:
        response = requests.get(url_stats, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # A estrutura da resposta pode variar, geralmente 'totalClicks' está na raiz ou em 'clicks'
        total_clicks = data.get("totalClicks", 0)
        if total_clicks == 0 and "clicks" in data:
             # Fallback caso a API retorne um objeto complexo em algumas versões
             total_clicks = sum(data["clicks"].values()) if isinstance(data["clicks"], dict) else data["clicks"]
             
        return int(total_clicks)
        
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API: {e}")
        raise

def update_history_and_chart(clicks):
    """Atualiza o CSV e gera o gráfico."""
    # Define fuso horário para Brasília
    tz_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%Y-%m-%d")
    
    # Garante que a pasta assets existe
    os.makedirs("assets", exist_ok=True)

    # 1. Atualizar CSV
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        # Garante que a coluna de dados é string para comparação correta
        df["data"] = df["data"].astype(str)
    else:
        df = pd.DataFrame(columns=["data", "cliques"])
        
    # Se já houver registro hoje, atualiza; senão, adiciona
    if hoje in df["data"].values:
        df.loc[df["data"] == hoje, "cliques"] = clicks
    else:
        novo_registro = pd.DataFrame([{"data": hoje, "cliques": clicks}])
        df = pd.concat([df, novo_registro], ignore_index=True)
        
    df.to_csv(CSV_PATH, index=False)
    
    # 2. Gerar Gráfico
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
    """Atualiza o número de cliques e a data no README."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        print("README.md não encontrado. Pulando atualização.")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Atualiza o número de cliques
    content = re.sub(
        r"<!-- CLICKS_START -->.*?<!-- CLICKS_END -->",
        f"<!-- CLICKS_START -->**{clicks}**<!-- CLICKS_END -->",
        content,
        flags=re.DOTALL
    )
    
    # Atualiza a data
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