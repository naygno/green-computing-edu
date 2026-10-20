import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import pytz
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CUTTLY_API_KEY = os.environ.get("CUTTLY_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not CUTTLY_API_KEY:
    raise ValueError("CUTTLY_API_KEY ausente nas variáveis de ambiente.")

CUTTLY_LINKS = {
    "pdf": "edu-ok",
    "video": "mini-guia-edu"
}

YOUTUBE_VIDEOS = {
    "mestre": "JK-YXGb64AM",
    "mv1": "IRFwnNDrrfk",
    "mv2": "1cBKbu1aVzw",
    "mv3": "FXA0WiQEX24",
    "mv4": "o2LVG3V4gk8"
}

CSV_PATH = "assets/telemetry_history.csv"
CHART_PATH = "assets/telemetry_chart.png"
README_PATH = "README.md"

def get_cuttly_telemetry(short_link: str) -> int:
    """Consulta Cutt.ly com tolerância a falhas."""
    url = f"https://cutt.ly/api/api.php?key={CUTTLY_API_KEY}&stats={short_link}"
    print(f"📡 [Cutt.ly] Consultando métricas para: {short_link}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        stats = data.get("stats", {})
        if stats.get("status") != 1:
            print(f"⚠️ [Cutt.ly] Erro na API para {short_link}. Payload: {data}")
            return 0
        clicks = int(stats.get("clicks", 0))
        print(f"✅ [Cutt.ly] Cliques ({short_link}): {clicks}")
        return clicks
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"⚠️ [Cutt.ly] Rate Limit Excedido (HTTP 429). Fallback.")
        else:
            print(f"⚠️ [Cutt.ly] Erro HTTP {e.response.status_code}.")
        return 0
    except Exception as e:
        print(f"⚠️ [Cutt.ly] Falha de conexão ({e}).")
        return 0

def get_youtube_telemetry() -> dict:
    """Consulta YouTube Data API v3 com tolerância a falhas."""
    if not YOUTUBE_API_KEY:
        print("⚠️ [YouTube] YOUTUBE_API_KEY não configurada. Ignorando.")
        return {"total_views": 0, "mestre_views": 0, "detalhes": {}}

    valid_ids = [v for v in YOUTUBE_VIDEOS.values() if not v.startswith("ID_SHORT_")]
    if not valid_ids:
        return {"total_views": 0, "mestre_views": 0, "detalhes": {}}

    ids_str = ",".join(valid_ids)
    url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={ids_str}&key={YOUTUBE_API_KEY}"
    print(f"📡 [YouTube] Consultando métricas para {len(valid_ids)} vídeos...")
    
    try:
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
    except Exception as e:
        print(f"⚠️ [YouTube] Falha na extração ({e}).")
        return {"total_views": 0, "mestre_views": 0, "detalhes": {}}

def update_history_and_chart(clicks_pdf: int, clicks_video: int, views_yt: int):
    """Atualiza CSV com blindagem monotônica e renderiza gráfico."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%Y-%m-%d")
    expected_cols = ["data", "cliques_pdf", "cliques_video", "views_yt"]
    
    os.makedirs("assets", exist_ok=True)

    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        df.columns = [str(c).strip().lower().replace("\ufeff", "") for c in df.columns]
        
        if "data" not in df.columns:
            for col in list(df.columns):
                if "dat" in col or "dia" in col:
                    df.rename(columns={col: "data"}, inplace=True)
                    break
            else:
                raise RuntimeError("ERRO CRÍTICO: Coluna 'data' ausente.")

        if "cliques_pdf" not in df.columns and "cliques" in df.columns:
            df.rename(columns={"cliques": "cliques_pdf"}, inplace=True)
            df["cliques_video"] = 0

        if "views_yt" not in df.columns:
            df["views_yt"] = 0

        df["data"] = df["data"].astype(str)

    # Identifica último valor histórico
    last_pdf = int(df["cliques_pdf"].iloc[-1]) if not df.empty else 0
    last_video = int(df["cliques_video"].iloc[-1]) if not df.empty else 0
    last_yt = int(df["views_yt"].iloc[-1]) if not df.empty else 0

    # BLINDAGEM MONOTÔNICA (Anti-Regressão)
    # Métricas cumulativas (views) NUNCA diminuem.
    # Se a API retornar 0 (falha) ou valor menor que o histórico (cache inconsistente),
    # o operador max() garante que o valor histórico prevaleça.
    final_pdf = max(clicks_pdf, last_pdf) if clicks_pdf > 0 else last_pdf
    final_video = max(clicks_video, last_video) if clicks_video > 0 else last_video
    final_yt = max(views_yt, last_yt)

    # Atualização atômica
    if hoje in df["data"].values:
        df.loc[df["data"] == hoje, "cliques_pdf"] = final_pdf
        df.loc[df["data"] == hoje, "cliques_video"] = final_video
        df.loc[df["data"] == hoje, "views_yt"] = final_yt
    else:
        novo_registro = pd.DataFrame([{
            "data": hoje, 
            "cliques_pdf": final_pdf, 
            "cliques_video": final_video,
            "views_yt": final_yt
        }])
        df = pd.concat([df, novo_registro], ignore_index=True)

    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"📊 [CSV] Histórico consolidado. Último: YT={final_yt}")

    # Renderização Bimodal
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    x = df["data"].astype(str).to_numpy()
    y_pdf = df["cliques_pdf"].astype(float).to_numpy()
    y_video = df["cliques_video"].astype(float).to_numpy()
    y_yt = df["views_yt"].astype(float).to_numpy()

    # Cutt.ly
    ax1.plot(x, y_pdf, marker='o', color='#3fb950', linewidth=2.5, markersize=6, label='PDF')
    ax1.fill_between(x, y_pdf, 0, color='#3fb950', alpha=0.15)
    ax1.plot(x, y_video, marker='s', color='#58a6ff', linewidth=2.5, markersize=6, label='Vídeo')
    ax1.fill_between(x, y_video, 0, color='#58a6ff', alpha=0.15)
    ax1.set_title("Engajamento Direto (Cutt.ly)", color="#f0f6fc", weight='bold')
    ax1.grid(True, linestyle='--', alpha=0.15, color="#768390")
    ax1.legend(facecolor='#161b22', edgecolor='#768390')
    ax1.tick_params(axis='x', rotation=45, colors="#8b949e")

    # YouTube
    ax2.plot(x, y_yt, marker='^', color='#f85149', linewidth=2.5, markersize=6, label='Views Totais')
    ax2.fill_between(x, y_yt, 0, color='#f85149', alpha=0.15)
    ax2.set_title("Alcance Multicanal (YouTube)", color="#f0f6fc", weight='bold')
    ax2.grid(True, linestyle='--', alpha=0.15, color="#768390")
    ax2.legend(facecolor='#161b22', edgecolor='#768390')
    ax2.tick_params(axis='x', rotation=45, colors="#8b949e")

    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=300, transparent=True)
    plt.close()
    print("📈 [Gráfico] Painel bimodal regenerado.")

def update_readme(clicks_pdf: int, clicks_video: int, yt_data: dict):
    """Atualiza âncoras no README."""
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br).strftime("%d/%m/%Y às %H:%M")
    
    if not os.path.exists(README_PATH):
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    if clicks_pdf > 0:
        content = re.sub(r"<!-- CLICKS_PDF_START -->.*?<!-- CLICKS_PDF_END -->", f"<!-- CLICKS_PDF_START -->**{clicks_pdf}**<!-- CLICKS_PDF_END -->", content, flags=re.DOTALL)
    if clicks_video > 0:
        content = re.sub(r"<!-- CLICKS_VIDEO_START -->.*?<!-- CLICKS_VIDEO_END -->", f"<!-- CLICKS_VIDEO_START -->**{clicks_video}**<!-- CLICKS_VIDEO_END -->", content, flags=re.DOTALL)
    
    total_views = yt_data.get("total_views", 0)
    detalhes = yt_data.get("detalhes", {})

    if total_views > 0:
        content = re.sub(r"<!-- YT_VIEWS_START -->.*?<!-- YT_VIEWS_END -->", f"<!-- YT_VIEWS_START -->**{total_views}**<!-- YT_VIEWS_END -->", content, flags=re.DOTALL)
        
        # Atualização individual
        for key, marker in [("mestre", "MESTRE"), ("mv1", "MV1"), ("mv2", "MV2"), ("mv3", "MV3"), ("mv4", "MV4")]:
            if YOUTUBE_VIDEOS[key] in detalhes:
                v = detalhes[YOUTUBE_VIDEOS[key]]["views"]
                pattern = f"<!-- YT_VIEWS_{marker}_START -->.*?<!-- YT_VIEWS_{marker}_END -->"
                replacement = f"<!-- YT_VIEWS_{marker}_START -->**{v}**<!-- YT_VIEWS_{marker}_END -->"
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    content = re.sub(r"<!-- DATE_START -->.*?<!-- DATE_END -->", f"<!-- DATE_START -->(Atualizado em {agora})<!-- DATE_END -->", content, flags=re.DOTALL)
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("📝 [README] Sincronizado.")

if __name__ == "__main__":
    c_pdf = get_cuttly_telemetry(CUTTLY_LINKS["pdf"])
    c_video = get_cuttly_telemetry(CUTTLY_LINKS["video"])
    yt_data = get_youtube_telemetry()
    
    update_history_and_chart(c_pdf, c_video, yt_data["total_views"])
    update_readme(c_pdf, c_video, yt_data)
    print("🚀 Telemetria Integrada executada com sucesso.")