"""Maerkte: Indizes + Tages-Gewinner/-Verlierer aus Konstituenten (yfinance)."""
import yfinance as yf

DAX = {
    "AIR.DE": "Airbus", "ALV.DE": "Allianz", "BAS.DE": "BASF", "BMW.DE": "BMW",
    "BAYN.DE": "Bayer", "BEI.DE": "Beiersdorf", "BNR.DE": "Brenntag",
    "CON.DE": "Continental", "DBK.DE": "Deutsche Bank", "DB1.DE": "Deutsche Börse",
    "DTG.DE": "Daimler Truck", "DTE.DE": "Telekom", "ENR.DE": "Siemens Energy",
    "EOAN.DE": "E.ON", "FRE.DE": "Fresenius", "FME.DE": "Fresenius Medical",
    "HNR1.DE": "Hannover Rück", "HEI.DE": "Heidelberg Materials", "HEN.DE": "Henkel",
    "IFX.DE": "Infineon", "LIN.DE": "Linde", "LHA.DE": "Lufthansa",
    "MBG.DE": "Mercedes-Benz", "MTX.DE": "MTU", "MRK.DE": "Merck",
    "PAH3.DE": "Porsche SE", "P911.DE": "Porsche AG", "RHM.DE": "Rheinmetall",
    "RWE.DE": "RWE", "SAP.DE": "SAP", "SHL.DE": "Siemens Healthineers",
    "SIE.DE": "Siemens", "SY1.DE": "Symrise", "SRT3.DE": "Sartorius",
    "VOW3.DE": "Volkswagen", "VNA.DE": "Vonovia", "ZAL.DE": "Zalando",
    "ADS.DE": "adidas",
}
DOW = {
    "MMM": "3M", "AXP": "American Express", "AMGN": "Amgen", "AAPL": "Apple",
    "AMZN": "Amazon", "BA": "Boeing", "CAT": "Caterpillar", "CVX": "Chevron",
    "CSCO": "Cisco", "KO": "Coca-Cola", "DIS": "Disney", "GS": "Goldman Sachs",
    "HD": "Home Depot", "HON": "Honeywell", "IBM": "IBM", "JNJ": "Johnson&Johnson",
    "JPM": "JPMorgan", "MCD": "McDonald's", "MRK": "Merck", "MSFT": "Microsoft",
    "NVDA": "Nvidia", "PG": "P&G", "CRM": "Salesforce", "TRV": "Travelers",
    "UNH": "UnitedHealth", "VZ": "Verizon", "V": "Visa", "WMT": "Walmart",
    "DOW": "Dow Inc", "SHW": "Sherwin-Williams",
}
NDX_MEGA = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "AVGO": "Broadcom", "TSLA": "Tesla",
    "NFLX": "Netflix", "AMD": "AMD", "INTC": "Intel", "ADBE": "Adobe",
    "COST": "Costco", "PEP": "PepsiCo", "QCOM": "Qualcomm",
}


def _index_line(label: str, ticker: str) -> str:
    hist = yf.Ticker(ticker).history(period="5d")
    if len(hist) < 2:
        return ""
    last, prev = hist["Close"].iloc[-1], hist["Close"].iloc[-2]
    pct = (last / prev - 1) * 100

    # Für Chart & Historie speichern
    try:
        from briefing import db as _db
        _db.store_market_history(label, round(float(last), 2), round(pct, 2))
    except Exception:  # noqa: BLE001 - Historie darf nie den Lauf bremsen
        pass

    arrow = "▲" if pct >= 0 else "▼"
    return f"{label}: {last:,.2f} ({arrow} {pct:+.2f} %)"


def _constituent_lines(label: str, mapping: dict) -> list[str]:
    try:
        data = yf.download(
            list(mapping), period="5d", interval="1d",
            progress=False, threads=True,
        )["Close"]
        if data is None or len(data) < 2:
            return []
        pct = (data.iloc[-1] / data.iloc[-2] - 1) * 100
        pct = pct.dropna().sort_values(ascending=False)
        if pct.empty:
            return []
        top = " · ".join(
            f"{mapping.get(t, t)} {v:+.1f} %" for t, v in pct.head(4).items()
        )
        flop = " · ".join(
            f"{mapping.get(t, t)} {v:+.1f} %"
            for t, v in sorted(pct.tail(3).items(), key=lambda kv: kv[1])
        )
        return [f"💪 {label} Top: {top}", f"📉 {label} Flop: {flop}"]
    except Exception as exc:  # noqa: BLE001
        print(f"[markets] Konstituenten {label}: {exc}")
        return []


def fetch(cfg: dict) -> dict:
    lines = []
    chart_data = []  # strukturierte Daten für Frontend-Balkendiagramm
    for ix in cfg["markets"]["indices"]:
        try:
            line = _index_line(ix["label"], ix["ticker"])
            if line:
                lines.append(line)
                # Strukturierte Daten für Chart mitschicken
                import re as _re
                m = _re.search(r"([\d.,]+)\s*\((.)\s*([+-][\d.,]+)", line)
                if m:
                    chart_data.append({
                        "label": ix["label"],
                        "value": m.group(1),
                        "arrow": m.group(2),
                        "pct": float(
                            m.group(3).replace("\xa0", "").replace(",", ".")
                        ),
                    })
        except Exception as exc:  # noqa: BLE001
            print(f"[markets] {ix['label']}: {exc}")
    for label, mapping in (
        ("DAX", DAX), ("Dow Jones", DOW), ("Nasdaq (Auswahl)", NDX_MEGA)
    ):
        lines.extend(_constituent_lines(label, mapping))
    return {
        "key": "markets",
        "title": "🌍 Märkte – DAX · Dow · Nasdaq",
        "lines": lines,
        "items": [],
        "comment": True,
        "chart_data": chart_data,
    }
