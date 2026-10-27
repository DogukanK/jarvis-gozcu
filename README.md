# jarvis-gozcu

Doğukan'ın Jarvis altyapısı için dış gözcü (GitHub Actions, 10 dakikada bir). VPS'ten ve evden bağımsız çalışır:
genel HTTPS uçları, sertifika süreleri ve VPS'in gönderdiği nabız. Sorun olunca Telegram'a yazar ve iş başarısız
olur (GitHub e-postası = yedek bildirim kanalı). Kaynağı: `jarvis/vps/gozcu/` (VPS'te ana kopya), nabız `jarvis/bin/gozcu`.
