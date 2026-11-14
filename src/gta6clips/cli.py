from __future__ import annotations

import argparse
import json
import logging
import time

from . import pipeline
from .config import load_config


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="gta6clips", description="GTA 6 klip otomasyonu")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="Twitch'te yeni popüler GTA 6 kliplerini bul")
    r = sub.add_parser("render", help="Bulunan klipleri indir ve dikey videoya kurgula")
    r.add_argument("--limit", type=int)
    sub.add_parser("upload", help="Kurgulanmış klipleri YouTube ve TikTok'a yükle")
    run = sub.add_parser("run", help="discover + render + upload; --loop ile sürekli")
    run.add_argument("--loop", action="store_true")
    run.add_argument("--interval", type=int, default=30, help="dakika")
    run.add_argument("--no-upload", action="store_true")
    v = sub.add_parser("vod", help="Uzun bir yayından ses zirvelerine göre kesit çıkar")
    v.add_argument("url")
    v.add_argument("--broadcaster", required=True)
    v.add_argument("--top", type=int, default=5)
    v.add_argument("--length", type=int, default=30)
    a = sub.add_parser("auth", help="Platform yetkilendirmesi")
    a.add_argument("platform", choices=["youtube", "tiktok"])
    sub.add_parser("status", help="Veritabanı özeti")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config)

    if args.cmd == "auth":
        if args.platform == "youtube":
            from .uploaders import youtube
            youtube.authorize()
        else:
            from .uploaders import tiktok
            tiktok.authorize()
        return

    db = pipeline.open_db(cfg)
    if args.cmd == "discover":
        pipeline.discover(cfg, db)
    elif args.cmd == "render":
        pipeline.render_pending(cfg, db, args.limit)
    elif args.cmd == "upload":
        pipeline.upload_pending(cfg, db)
    elif args.cmd == "vod":
        pipeline.process_vod(cfg, db, args.url, args.broadcaster, args.top, args.length)
    elif args.cmd == "status":
        print(json.dumps(db.stats(), indent=2))
    elif args.cmd == "run":
        while True:
            try:
                pipeline.discover(cfg, db)
                pipeline.render_pending(cfg, db)
                if not args.no_upload:
                    pipeline.upload_pending(cfg, db)
            except Exception:
                logging.exception("Tur başarısız, sonraki turda tekrar denenecek")
                if not args.loop:
                    raise
            if not args.loop:
                break
            logging.info("%d dakika bekleniyor...", args.interval)
            time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
