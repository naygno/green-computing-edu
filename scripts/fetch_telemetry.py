import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import re
import pytz

# Carregamento da chave da API
CUTTLY_API_KEY = os.environ.get("CUTTLY_API_KEY")
if not CUTTLY_API_KEY:
    raise ValueError("CUTTLY_API_KEY ausente nos Secrets.")

# Links a serem monitorados
LINKS = {
    "pdf": "edu-ok",
    "video": "mini-guia-edu"
}

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_telemetry(short_link: str) -> int:
    """Consulta o total acumulado de cliques via Cutt.ly Regular API."""
    url = f"https://cutt.ly/api/api.php?key={CUTTLY_API_KEY}&stats={short_link}"
    print(f"📡 Consultando métricas para: {short_link}...")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    stats = data.get("stats", {})
    if stats.get("status") != 1:
        raise RuntimeError(f"Erro no Cutt.ly para {short_link}. Payload: {data}")
        
    clicks = int(stats.get("clicks", 0))
    print(f"✅ Cliques ({short_link}): {clicks}")
    return clicks

def update_history_and_chart(clicks_pdf: int, clicks_video: int):
    """Atualiza o CSV com migração segura de schema e plota gráfico duplo."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%Y-%m-%d")
    expected_cols = ["data", "cliques_pdf", "cliques_video"]
    
    os.makedirs("assets", exist_ok=True)

    df = None
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0:
        df = pd.read_csv(CSV_PATH)
        # Migração de schema: se for o CSV antigo, renomeia a coluna e cria a nova
        if "cliques" in df.columns:
            df.rename(columns={"cliques": "cliques_pdf"}, inplace=True)
            df["cliques_video"] = 0
            print("🔄 Schema do CSV migrado para Telemetria Dupla com sucesso.")
        df["data"] = df["data"].astype(str)

    if df is None or df.empty:
        df = pd.DataFrame(columns=expected_cols)
        
    # Atualiza ou insere registro de hoje
    if hoje in df["data"].values:
        df.loc[df["data"] == hoje, "cliques_pdf"] = clicks_pdf
        df.loc[df["data"] == hoje, "cliques_video"] = clicks_video
    else:
        novo_registro = pd.DataFrame([{"data": hoje, "cliques_pdf": clicks_pdf, "cliques_video": clicks_video}])
        df = pd.concat([df, novo_registro], ignore_index=True)
        
    df.to_csv(CSV_PATH, index=False)
    
    # Renderização visual (Gráfico Duplo)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))
    
    x = df["data"].astype(str).to_numpy()
    y_pdf = df["cliques_pdf"].astype(float).to_numpy()
    y_video = df["cliques_video"].astype(float).to_numpy()

    ax.plot(x, y_pdf, marker='o', color='#3fb950', linewidth=2.5, markersize=8, label='Adesão PDF (edu-ok)')
    ax.fill_between(x, y_pdf, 0, color='#3fb950', alpha=0.2)
    
    ax.plot(x, y_video, marker='s', color='#58a6ff', linewidth=2.5, markersize=8, label='Views Vídeo (mini-guia-edu)')
    ax.fill_between(x, y_video, 0, color='#58a6ff', alpha=0.2)
    
    ax.set_title("Evolução de Engajamento (PDF vs Vídeo)", fontsize=13, pad=15, color="#f0f6fc")
    ax.set_xlabel("Data", fontsize=11, labelpad=10, color="#8b949e")
    ax.set_ylabel("Total de Cliques", fontsize=11, labelpad=10, color="#8b949e")
    ax.grid(True, linestyle='--', alpha=0.2, color="#768390")
    ax.legend(loc="upper left", facecolor='#161b22', edgecolor='#768390')
    plt.xticks(rotation=45, color="#8b949e")
    plt.yticks(color="#8b949e")
    plt.tight_layout()
    
    plt.savefig(CHART_PATH, dpi=300, transparent=True)
    plt.close()

def update_readme(clicks_pdf: int, clicks_video: int):
    """Substitui as âncoras duplas no README."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = re.sub(r"<!-- CLICKS_PDF_START -->.*?<!-- CLICKS_PDF_END -->", f"<!-- CLICKS_PDF_START -->**{clicks_pdf}**<!-- CLICKS_PDF_END -->", content, flags=re.DOTALL)
    content = re.sub(r"<!-- CLICKS_VIDEO_START -->.*?<!-- CLICKS_VIDEO_END -->", f"<!-- CLICKS_VIDEO_START -->**{clicks_video}**<!-- CLICKS_VIDEO_END -->", content, flags=re.DOTALL)
    content = re.sub(r"<!-- DATE_START -->.*?<!-- DATE_END -->", f"<!-- DATE_START -->(Atualizado em {agora})<!-- DATE_END -->", content, flags=re.DOTALL)
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    c_pdf = get_telemetry(LINKS["pdf"])
    c_video = get_telemetry(LINKS["video"])
    update_history_and_chart(c_pdf, c_video)
    update_readme(c_pdf, c_video)
    print("✅ Telemetria Dupla sincronizada com sucesso.")