import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# 1. Carregamento estrito das credenciais do Cutt.ly
CUTTLY_API_KEY = os.environ.get("CUTTLY_API_KEY")
CUTTLY_SHORT_LINK = os.environ.get("CUTTLY_SHORT_LINK")

if not CUTTLY_API_KEY or not CUTTLY_SHORT_LINK:
    raise ValueError("Variáveis ausentes. Verifique se CUTTLY_API_KEY e CUTTLY_SHORT_LINK estão nos Secrets.")

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry() -> int:
    """Consulta o total acumulado de cliques via Cutt.ly Regular API."""
    url = f"https://cutt.ly/api/api.php?key={CUTTLY_API_KEY}&stats={CUTTLY_SHORT_LINK}"
    
    print(f"📡 Consultando métricas no Cutt.ly para: {CUTTLY_SHORT_LINK}...")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    stats = data.get("stats", {})
    status = stats.get("status")
    
    if status != 1:
        error_msg = f"Cutt.ly retornou status de erro {status}. Payload: {data}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)
        
    total_clicks = stats.get("clicks", 0)
    print(f"✅ Total de cliques obtidos com sucesso: {total_clicks}")
    return int(total_clicks)

def update_history_and_chart(clicks: int):
    """Atualiza a série histórica em CSV e plota gráfico estaticamente tipado."""
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
        # Conversão explícita para arrays NumPy (elimina diagnósticos do Pylance/Pyright)
        x = df["data"].astype(str).to_numpy()
        y = df["cliques"].astype(float).to_numpy()

        ax.plot(x, y, marker='o', color='#3fb950', linewidth=2.5, markersize=8)
        ax.fill_between(x, y, 0, color='#3fb950', alpha=0.2)
    
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
    """Substitui os delimitadores no README pelo valor atualizado."""
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
    print("Telemetria, gráfico e README sincronizados com sucesso.")