import os
import urllib.request
from PIL import Image, ImageDraw

def setup_assets():
    os.makedirs("assets/screenshots", exist_ok=True)
    
    # 1. Gerar o QR Code oficial para https://cutt.ly/edu-ok com as cores do projeto
    qr_path = "assets/qr_cuttly_edu_ok.png"
    print("📡 Baixando QR Code de telemetria do Cutt.ly...")
    url = "https://api.qrserver.com/v1/create-qr-code/?size=600x600&data=https://cutt.ly/edu-ok&color=40-200-111&bgcolor=17-20-24"
    urllib.request.urlretrieve(url, qr_path)
    print(f"✅ QR Code gravado em: {qr_path}")

    # 2. Criar placeholders transitórios para bateria caso ainda não existam
    # (Permite ao LaTeX compilar de imediato enquanto você captura os prints no Pixel 8)
    for name in ["print_bateria1.png", "print_bateria2.png"]:
        path = f"assets/screenshots/{name}"
        if not os.path.exists(path):
            img = Image.new("RGB", (1080, 2400), color=(17, 20, 24))
            draw = ImageDraw.Draw(img)
            draw.text((300, 1200), f"Substituir por print real:\n{name}", fill=(241, 196, 15))
            img.save(path)
            print(f"⚠️ Placeholder temporário criado: {path}")

if __name__ == "__main__":
    setup_assets()