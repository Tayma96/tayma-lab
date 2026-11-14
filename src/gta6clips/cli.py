from __future__ import annotations

import argparse
import json
import logging

from . import pipeline
from .config import load_config


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="gta6clips", description="GTA 6 klip otomasyonu")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="Twitch'te yeni popüler GTA 6 kliplerini bul")
    r = sub.add_parser("render", help="Bulunan klipleri analiz et, iyileri kurgula")
    r.add_argument("--limit", type=int)
    sub.add_parser("upload", help="Kurgulanmış klipleri öncelik sırasıyla YouTube ve TikTok'a yükle")
    sub.add_parser("live", help="Sadece canlı avcıyı çalıştır (sohbet patlamalarında klip oluşturur)")
    run = sub.add_parser("run", help="Tek tur ya da --loop ile her şey sürekli (canlı avcı dahil)")
    run.add_argument("--loop", action="store_true")
    run.add_argument("--no-upload", action="store_true")
    run.add_argument("--no-live", action="store_true")
    v = sub.add_parser("vod", help="Uzun bir yayından en iyi anları çıkar")
    v.add_argument("url")
    v.add_argument("--broadcaster", required=True)
    v.add_argument("--top", type=int, default=5)
    v.add_argument("--length", type=int, default=40)
    sub.add_parser("stats", help="YouTube izlenmelerini çek, yayıncı performansını göster")
    a = sub.add_parser("auth", help="Platform yetkilendirmesi")
    a.add_argument("platform", choices=["youtube", "tiktok", "twitch"])
    sub.add_parser("status", help="Veritabanı özeti")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
    cfg = load_config(args.config)

    if args.cmd == "auth":
        if args.platform == "youtube":
            from .uploaders import youtube
            youtube.authorize()
        elif args.platform == "tiktok":
            from .uploaders import tiktok
            tiktok.authorize()
        else:
            from .twitch import TwitchUser
            TwitchUser.from_env().authorize()
        return

    db = pipeline.open_db(cfg)
    if args.cmd == "discover":
        pipeline.discover(cfg, db)
    elif args.cmd == "render":
        pipeline.render_pending(cfg, db, args.limit)
    elif args.cmd == "upload":
        pipeline.upload_pending(cfg, db)
    elif args.cmd == "live":
        from .live import run_live
        run_live(cfg, db)
    elif args.cmd == "vod":
        pipeline.process_vod(cfg, db, args.url, args.broadcaster, args.top, args.length)
    elif args.cmd == "stats":
        pipeline.refresh_stats(cfg, db)
        print(json.dumps(db.stats(), indent=2, ensure_ascii=False))
    elif args.cmd == "status":
        print(json.dumps(db.stats(), indent=2, ensure_ascii=False))
    elif args.cmd == "run":
        if args.loop:
            pipeline.run_forever(cfg, upload=not args.no_upload, live=not args.no_live)
        else:
            pipeline.discover(cfg, db)
            pipeline.render_pending(cfg, db)
            if not args.no_upload:
                pipeline.upload_pending(cfg, db)


if __name__ == "__main__":
    main()
