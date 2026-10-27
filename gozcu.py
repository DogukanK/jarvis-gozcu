#!/usr/bin/env python3
"""Jarvis dış gözcüsü (GitHub Actions, 10 dk): VPS'ten ve evden BAĞIMSIZ yoklar.

Yoklamalar:
  merhaba, dokploy   https 200 (VPS + Traefik + Swarm ayakta mı)
  nabiz              VPS'teki jarvis-bulut 10 dk'da bir NABIZ değişkenini yazar (bin/gozcu nabiz); 40 dk eskiyse
                     konteyner ya da VPS'in çıkışı ölü
  bekci              nabızdaki bekçi yaşı (bekçi 2 dk'da bir çalışır) 15 dk'yı geçtiyse bekçi durmuş
  telegram           nabızdaki "gidemeyen" bildirim 20 dk'dan eski: Telegram'a gidemiyor (yedek kanal: bu iş
                     başarısız olur, GitHub e-posta atar)
  tls:<alan>         genel sertifikalar >= 14 gün
Bir sorun art arda 2 çalışmada görülürse BİR kez bildirilir (Telegram + işin başarısız olması = GitHub e-postası),
düzelince bir kez "düzeldi". Durum actions/cache ile taşınır (durum.json). Loglar herkese açık olabilir: değer basma.
"""
import json
import os
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DURUM = "durum.json"
HTTP = {"merhaba": "https://merhaba.kurnaz.cloud/", "dokploy": "https://dokploy.kurnaz.cloud/"}
TLS = ["merhaba.kurnaz.cloud", "dokploy.kurnaz.cloud", "hermes.kurnaz.cloud"]
ACIKLAMA = {
    "merhaba": "VPS'teki merhaba.kurnaz.cloud cevap vermiyor (VPS, Traefik ya da Swarm)",
    "dokploy": "Dokploy paneli cevap vermiyor",
    "nabiz": "jarvis-bulut nabzı kesildi (VPS ya da jarvis-bulut konteyneri ölü / internetsiz)",
    "bekci": "VPS bekçisi çalışmıyor (zamanlayıcı durmuş)",
    "telegram": "Bildirimler Telegram'a gidemiyor (bu e-posta yedek kanal)",
}


def http(url):
    try:
        istek = urllib.request.Request(url, headers={"User-Agent": "jarvis-gozcu"})
        with urllib.request.urlopen(istek, timeout=15) as y:
            return y.status == 200, f"HTTP {y.status}"
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__


def tls_gun(alan):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((alan, 443), timeout=10) as s, ctx.wrap_socket(s, server_hostname=alan) as t:
            c = t.getpeercert()
        bitis = datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        gun = (bitis - datetime.now(timezone.utc)).days
        return gun >= 14, f"{gun} gün"
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__


def yokla():
    s = {ad: http(u) for ad, u in HTTP.items()}
    try:
        n = json.loads(os.environ.get("NABIZ") or "{}")
    except ValueError:
        n = {}
    simdi = time.time()
    yas = (simdi - n.get("t", 0)) / 60
    s["nabiz"] = (yas <= 40, f"{round(yas)} dk önce" if n else "nabız yok")
    if n and yas <= 40:
        s["bekci"] = (n.get("bekci_dk", 0) <= 15, f"bekçi {n.get('bekci_dk')} dk önce")
        s["telegram"] = (n.get("gidemeyen_dk", 0) <= 20, f"{n.get('gidemeyen', 0)} bildirim bekliyor")
    for a in TLS:
        s["tls:" + a] = tls_gun(a)
    return s


def telegram(metin):
    tok, sohbet = os.environ.get("TG_TOKEN"), os.environ.get("TG_SOHBET")
    if not tok or not sohbet:
        return False
    try:
        veri = urllib.parse.urlencode({"chat_id": sohbet, "text": metin}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", veri, timeout=15).close()
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    try:
        eski = json.load(open(DURUM))
    except (OSError, ValueError):
        eski = {}
    yeni, olaylar = {}, []
    for ad, (iyi, ayr) in yokla().items():
        o = eski.get(ad) or {"sayac": 0, "uyarildi": False, "t": time.time()}
        d = dict(o)
        if iyi:
            if o.get("uyarildi"):
                dk = round((time.time() - o.get("t", time.time())) / 60)
                olaylar.append(("duzeldi", f"Jarvis gözcü: {ad} düzeldi (~{dk} dk sürdü)."))
            d = {"sayac": 0, "uyarildi": False, "t": time.time()}
        else:
            d["sayac"] = o.get("sayac", 0) + 1
            if d["sayac"] == 1:
                d["t"] = time.time()
            if d["sayac"] >= 2 and not o.get("uyarildi"):
                aciklama = ACIKLAMA.get(ad) or f"{ad.split(':', 1)[1]} sertifikası 14 günden az ya da okunamıyor"
                olaylar.append(("dustu", f"Jarvis gözcü (GitHub, VPS dışı): {aciklama} ({ayr})."))
                d["uyarildi"] = True
        print(f"{ad:28} {'iyi' if iyi else 'SORUN'}  {ayr}")
        yeni[ad] = d
    json.dump(yeni, open(DURUM, "w"))
    if os.environ.get("DENEME") == "true":
        olaylar.append(("deneme", "Jarvis gözcü (GitHub) deneme mesajı: dış izleyici Telegram'a ulaşabiliyor."))
    dustu = False
    for tur, metin in olaylar:
        print(f"{tur}: {metin}  telegram={'gitti' if telegram(metin) else 'gidemedi'}")
        dustu |= tur == "dustu"
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"yeni_olay={1 if dustu else 0}\n")


if __name__ == "__main__":
    sys.exit(main())
