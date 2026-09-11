import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# 1. Carregamento estrito das credenciais do Bitly
BITLY_TOKEN = os.environ.get("BITLY_TOKEN")
BITLY_LINK = os.environ.get("BITLY_LINK")

if not BITLY_TOKEN or not BITLY_LINK:
    raise ValueError("Variáveis ausentes. Verifique se BITLY_TOKEN e BITLY_LINK estão configurados nos Secrets.")

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry() -> int:
    """Consulta o total acumulado de cliques via Bitly API v4."""
    # Sanitização: remove https://, http:// e barras residuais
    clean_link = BITLY_LINK.replace("https://", "").replace("http://", "").strip("/")
    
    url = f"https://api-ssl.bitly.com/v4/bitlinks/{clean_link}/clicks/summary?unit=day&units=-1"
    headers = {
        "Authorization": f"Bearer {BITLY_TOKEN}",
        "Accept": "application/json"
    }
    
    print(f"📡 Consultando métricas do link Bitly: {clean_link}...")
    response = requests.get(url, headers=headers, timeout=15)
    
    if response.status_code != 200:
        print(f"❌ Erro Bitly API ({response.status_code}): {response.text}")
        response.raise_for_status()
        
    data = response.json()
    total_clicks = data.get("total_clicks", 0)
    print(f"✅ Total de cliques obtidos com sucesso: {total_clicks}")
    return int(total_clicks)

def update_history_and_chart(clicks: int):
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
        ax.plot(df["data"], df["cliques"], marker='o', color='#3fb950', linewidth=2.5, markersize=8)
        ax.fill_between(df["data"], df["cliques"], color='#3fb950', alpha=0.2)
    
    ax.set_title("Evolução de Adesão à Campanha (Cliques Validados)", fontsize=13, pad=15, color="#f0f6fc")
    ax.set_xlabel("Data", fontsize=11, labelpad=10, color="#8b949e")
    ax.set_ylabel("Total de Cliques", fontsize=11, labelpad=10, color="#8b949e")
    ax.grid(True, linestyle='--', alpha=0.2, color="#768390")
    plt.xticks(rotation=45, color="#8b949e")
    plt.yticks(color="#8b949e")
    plt.tight_layout()
    
    plt.savefig(CHART_PATH, dpi=300, transparent=True)
    plt.close()

def update_readme(clicks: int):
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        print("Aviso: README.md não encontrado.")
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
    update_history_and_chart(total_clicks)
    update_readme(total_clicks)
    print("Telemetria e README sincronizados com sucesso.")