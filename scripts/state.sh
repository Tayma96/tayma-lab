#!/usr/bin/env bash
# Çalıştırmalar arasında korunan durum: veritabanı, yüz kamerası konumları ve yenilenen giriş token'ları.
# Public repoda güvenli olsun diye STATE_KEY (GitHub Secret) ile AES-256 şifrelenir.
#   scripts/state.sh pack    -> state.enc oluşturur
#   scripts/state.sh unpack  -> state.enc varsa açar
set -euo pipefail

if [ -z "${STATE_KEY:-}" ]; then
  echo "::error::STATE_KEY secret'ı yok. Repo > Settings > Secrets and variables > Actions'a ekle (uzun rastgele bir şifre)."
  exit 1
fi

FILES=(data/clips.db data/facecams.json secrets/twitch_user_token.json secrets/youtube_token.json secrets/tiktok_token.json)

case "$1" in
  pack)
    existing=()
    for f in "${FILES[@]}"; do [ -f "$f" ] && existing+=("$f"); done
    [ ${#existing[@]} -eq 0 ] && { echo "Kaydedilecek durum yok"; exit 0; }
    # Veritabanının WAL kayıtlarını ana dosyaya yaz ki tek dosya yeterli olsun
    [ -f data/clips.db ] && python -c "import sqlite3; sqlite3.connect('data/clips.db').execute('PRAGMA wal_checkpoint(TRUNCATE)')"
    tar czf - "${existing[@]}" | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:STATE_KEY -out state.enc
    echo "Durum kaydedildi: ${existing[*]}"
    ;;
  unpack)
    if [ -f state.enc ]; then
      openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:STATE_KEY -in state.enc | tar xzf -
      echo "Önceki durum yüklendi"
    else
      echo "Önceki durum yok (ilk çalıştırma)"
    fi
    ;;
esac
