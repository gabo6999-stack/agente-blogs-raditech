"""Cuarta tanda: que URLs estan CONSISTENTEMENTE rotas vs flaky. 3 intentos c/u, espaciados."""
import time

import requests

BASE = "https://propertyledger.us"
CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
GBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

PATHS = [
    "/",
    "/contact/",
    "/monthly-accounting/",
    "/property-management-accounting/",
    "/hoa-condo-accounting/",
    "/property-management-trust-accounting/",
    "/property-management-financial-statements/",
    "/hoa-accounting-basics-guide-board-members-treasurers/",
    "/what-is-trust-accounting-property-management-guide/",
    "/property-management-bookkeeping-vs-accounting/",
    "/setting-up-property-management-chart-of-accounts/",
]

print(f"{'path':<56}{'Chrome x3':<22}{'Googlebot x3'}")
print("-" * 100)
for p in PATHS:
    row = {}
    for ua_name, ua in (("chrome", CHROME), ("gbot", GBOT)):
        codes = []
        for _ in range(3):
            try:
                r = requests.get(BASE + p, headers={"User-Agent": ua, "Cache-Control": "no-cache"},
                                 allow_redirects=False, timeout=30)
                codes.append(str(r.status_code) + (">" if r.headers.get("location") else ""))
            except Exception:
                codes.append("ERR")
            time.sleep(2)
        row[ua_name] = codes
    print(f"{p[:55]:<56}{','.join(row['chrome']):<22}{','.join(row['gbot'])}")

print()
print("Leyenda: '>' = trae cabecera Location (redirige).")
print("Un codigo que se repite 3/3 es estable; mezclado = flaky (edge/WAF).")
