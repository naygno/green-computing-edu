import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import pytz
import requests

# Tenta carregar o arquivo .env localmente caso a biblioteca python-dotenv esteja instalada
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Chaves de API (lidas do .env local ou dos Secrets do GitHub Actions)
CUTTLY_API_KEY = os.environ.get("CUTTLY_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not CUTTLY_API_KEY:
    raise ValueError("CUTTLY_API_KEY ausente nas variáveis de ambiente.")

# Links do Cutt.ly monitorados
CUTTLY_LINKS = {
    "pdf": "edu-ok",            # Confirmação de download do PDF
    "video": "mini-guia-edu"    # Redirecionador exclusivo para o Vídeo Mestre (141s)
}

# Suíte de vídeos do YouTube monitorados via Data API v3
YOUTUBE_VIDEOS = {
    "mestre": "JK-YXGb64AM",    # Vídeo Consolidado (141s)
    "mv1": "IRFwnNDrrfk",       # Parte 1: DNS Particular (29s)
    "mv2": "1cBKbu1aVzw",       # Parte 2: Economia de Dados (34s)
    "mv3": "FXA0WiQEX24",       # Parte 3: WhatsApp Mídia (49s)
    "mv4": "o2LVG3V4gk8"        # Parte 4: Economia de Bateria (33s)
}

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_cuttly_telemetry(short_link: str) -> int:
    """Consulta o total acumulado de cliques via Cutt.ly Regular API."""
    url = f"https://cutt.ly/api/api.php?key={CUTTLY_API_KEY}&stats={short_link}"
    print(f"📡 [Cutt.ly] Consultando métricas para: {short_link}...")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    stats = data.get("stats", {})
    if stats.get("status") != 1:
        raise RuntimeError(f"Erro no Cutt.ly para {short_link}. Payload: {data}")
        
    clicks = int(stats.get("clicks", 0))
    print(f"✅ [Cutt.ly] Cliques ({short_link}): {clicks}")
    return clicks

def get_youtube_telemetry() -> dict:
    """Consulta views e likes em lote via YouTube Data API v3 (Custo: 1 unidade de cota)."""
    if not YOUTUBE_API_KEY:
        print("⚠️ [YouTube] YOUTUBE_API_KEY não configurada. Ignorando coleta de vídeo.")
        return {"total_views": 0, "mestre_views": 0, "detalhes": {}}

    valid_ids = [v for v in YOUTUBE_VIDEOS.values() if not v.startswith("ID_SHORT_")]
    if not valid_ids:
        print("⚠️ [YouTube] Nenhum ID de vídeo válido configurado.")
        return {"total_views": 0, "mestre_views": 0, "detalhes": {}}

    ids_str = ",".join(valid_ids)
    url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={ids_str}&key={YOUTUBE_API_KEY}"
    print(f"📡 [YouTube] Consultando métricas para {len(valid_ids)} vídeos...")
    
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    detalhes = {}
    total_views = 0
    mestre_views = 0

    for item in data.get("items", []):
        v_id = item["id"]
        stats = item.get("statistics", {})
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        
        detalhes[v_id] = {"views": views, "likes": likes}
        total_views += views
        
        if v_id == YOUTUBE_VIDEOS["mestre"]:
            mestre_views = views

    print(f"✅ [YouTube] Views Totais: {total_views} (Vídeo Mestre: {mestre_views})")
    return {"total_views": total_views, "mestre_views": mestre_views, "detalhes": detalhes}

def update_history_and_chart(clicks_pdf: int, clicks_video: int, views_yt: int):
    """Atualiza o CSV com migração de schema e renderiza gráfico de eixo duplo (Twin Axis)."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%Y-%m-%d")
    expected_cols = ["data", "cliques_pdf", "cliques_video", "views_yt"]
    
    os.makedirs("assets", exist_ok=True)

    df = None
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0:
        df = pd.read_csv(CSV_PATH)
        # Migração segura para acomodar telemetria do YouTube
        if "views_yt" not in df.columns:
            df["views_yt"] = 0
            print("🔄 [CSV] Coluna 'views_yt' adicionada ao histórico existente.")
        df["data"] = df["data"].astype(str)

    if df is None or df.empty:
        df = pd.DataFrame(columns=expected_cols)
        
    # Atualiza registro de hoje ou concatena novo
    if hoje in df["data"].values:
        df.loc[df["data"] == hoje, "cliques_pdf"] = clicks_pdf
        df.loc[df["data"] == hoje, "cliques_video"] = clicks_video
        df.loc[df["data"] == hoje, "views_yt"] = views_yt
    else:
        novo_registro = pd.DataFrame([{
            "data": hoje, 
            "cliques_pdf": clicks_pdf, 
            "cliques_video": clicks_video,
            "views_yt": views_yt
        }])
        df = pd.concat([df, novo_registro], ignore_index=True)
        
    df.to_csv(CSV_PATH, index=False)
    
    # Renderização Gráfica com Eixo Duplo (Twin Axis)
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()  # Eixo secundário para visualizações do YouTube

    x = df["data"].astype(str).to_numpy()
    y_pdf = df["cliques_pdf"].astype(float).to_numpy()
    y_video = df["cliques_video"].astype(float).to_numpy()
    y_yt = df["views_yt"].astype(float).to_numpy()

    # Eixo 1 (Esquerda): Cliques Diretos Cutt.ly (Escala baixa)
    line1 = ax1.plot(x, y_pdf, marker='o', color='#3fb950', linewidth=2.5, markersize=7, label='Adesão PDF (edu-ok)')
    ax1.fill_between(x, y_pdf, 0, color='#3fb950', alpha=0.15)
    
    line2 = ax1.plot(x, y_video, marker='s', color='#58a6ff', linewidth=2.5, markersize=7, label='Cliques Vídeo (mini-guia-edu)')
    ax1.fill_between(x, y_video, 0, color='#58a6ff', alpha=0.15)

    # Eixo 2 (Direita): Visualizações YouTube (Escala alta)
    line3 = ax2.plot(x, y_yt, marker='^', color='#f85149', linewidth=2.0, linestyle='--', markersize=7, label='Views YouTube (Total)')
    
    # Configurações de layout e títulos
    ax1.set_title("Telemetria Integrada: Engajamento Cutt.ly vs. Alcance YouTube", fontsize=13, pad=15, color="#f0f6fc")
    ax1.set_xlabel("Data", fontsize=11, labelpad=10, color="#8b949e")
    ax1.set_ylabel("Cliques Diretos (Cutt.ly)", fontsize=11, labelpad=10, color="#8b949e")
    ax2.set_ylabel("Visualizações Globais (YouTube)", fontsize=11, labelpad=10, color="#f85149")
    
    ax1.grid(True, linestyle='--', alpha=0.15, color="#768390")
    
    # Unificação das legendas dos dois eixos
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", facecolor='#161b22', edgecolor='#768390')
    
    ax1.tick_params(axis='x', rotation=45, colors="#8b949e")
    ax1.tick_params(axis='y', colors="#8b949e")
    ax2.tick_params(axis='y', colors="#f85149")
    
    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=300, transparent=True)
    plt.close()
    print("📈 [Gráfico] Renderização com eixo duplo concluída em assets/telemetry_chart.png.")

def update_readme(clicks_pdf: int, clicks_video: int, views_yt: int):
    """Atualiza as âncoras regex dinâmicas no README.md."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = re.sub(r"<!-- CLICKS_PDF_START -->.*?<!-- CLICKS_PDF_END -->", f"<!-- CLICKS_PDF_START -->**{clicks_pdf}**<!-- CLICKS_PDF_END -->", content, flags=re.DOTALL)
    content = re.sub(r"<!-- CLICKS_VIDEO_START -->.*?<!-- CLICKS_VIDEO_END -->", f"<!-- CLICKS_VIDEO_START -->**{clicks_video}**<!-- CLICKS_VIDEO_END -->", content, flags=re.DOTALL)
    content = re.sub(r"<!-- YT_VIEWS_START -->.*?<!-- YT_VIEWS_END -->", f"<!-- YT_VIEWS_START -->**{views_yt}**<!-- YT_VIEWS_END -->", content, flags=re.DOTALL)
    content = re.sub(r"<!-- DATE_START -->.*?<!-- DATE_END -->", f"<!-- DATE_START -->(Atualizado em {agora})<!-- DATE_END -->", content, flags=re.DOTALL)
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("📝 [README] Marcadores sincronizados.")

if __name__ == "__main__":
    c_pdf = get_cuttly_telemetry(CUTTLY_LINKS["pdf"])
    c_video = get_cuttly_telemetry(CUTTLY_LINKS["video"])
    yt_data = get_youtube_telemetry()
    
    update_history_and_chart(c_pdf, c_video, yt_data["total_views"])
    update_readme(c_pdf, c_video, yt_data["total_views"])
    print("🚀 Telemetria Integrada (Cutt.ly + YouTube) executada com sucesso.")