import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# 1. Carregamento estrito 1:1 das secrets confirmadas no repositório
SHORT_IO_API_KEY = os.environ.get("SHORT_IO_API_KEY")
DOMAIN_ID = os.environ.get("DOMAIN_ID")
SHORT_IO_LINK_ID = os.environ.get("SHORT_IO_LINK_ID")

# Validação determinística
if not all([SHORT_IO_API_KEY, DOMAIN_ID, SHORT_IO_LINK_ID]):
    raise ValueError("Variáveis de ambiente ausentes. Verifique: SHORT_IO_API_KEY, DOMAIN_ID e SHORT_IO_LINK_ID.")

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry() -> int:
    """Consulta o total acumulado de cliques do link no host de estatísticas (ADR-03)."""
    headers = {
        "authorization": SHORT_IO_API_KEY,
        "accept": "application/json"
    }

    url = f"https://statistics.short.io/statistics/link/{SHORT_IO_LINK_ID}?period=total"
    print(f"📡 Consultando métricas do link {SHORT_IO_LINK_ID}...")
    
    response = requests.get(url, headers=headers, timeout=15)
    
    # Se o ID do link não responder 200, consulta o domínio via DOMAIN_ID
    if response.status_code != 200:
        print(f"⚠️ Link não respondeu 200 (HTTP {response.status_code}). Consultando domínio {DOMAIN_ID}...")
        url_domain = f"https://statistics.short.io/statistics/domain/{DOMAIN_ID}?period=total"
        response = requests.get(url_domain, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        total = data.get("clicks", data.get("humanClicks", 0))
        return int(total)

    response.raise_for_status()
    data = response.json()
    total = data.get("totalClicks")
    if total is None:
        total = data.get("humanClicks", data.get("clicks", 0))
        
    return int(total)

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
    print(f"✅ Total de cliques obtidos: {total_clicks}")
    update_history_and_chart(total_clicks)
    update_readme(total_clicks)
    print("Telemetria e README atualizados com sucesso.")