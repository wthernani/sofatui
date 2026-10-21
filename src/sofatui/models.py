"""Data models for SofaTUI football matches, incidents, statistics, commentary, lineups, and standings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


COUNTRY_ALPHA3_MAP: dict[str, str] = {
    "england": "ENG", "spain": "ESP", "italy": "ITA", "germany": "GER", "france": "FRA",
    "portugal": "POR", "netherlands": "NED", "brazil": "BRA", "argentina": "ARG",
    "turkey": "TUR", "türkiye": "TUR", "scotland": "SCO", "belgium": "BEL",
    "austria": "AUT", "switzerland": "SUI", "czechia": "CZE", "czech republic": "CZE",
    "slovakia": "SVK", "ukraine": "UKR", "croatia": "CRO", "serbia": "SRB",
    "norway": "NOR", "denmark": "DEN", "sweden": "SWE", "greece": "GRE",
    "azerbaijan": "AZE", "hungary": "HUN", "romania": "ROU", "bulgaria": "BUL",
    "poland": "POL", "cyprus": "CYP", "israel": "ISR", "slovenia": "SVN",
    "mexico": "MEX", "usa": "USA", "united states": "USA", "saudi arabia": "KSA",
    "colombia": "COL", "uruguay": "URU", "chile": "CHI", "bolivia": "BOL",
    "paraguay": "PAR", "ecuador": "ECU", "peru": "PER", "venezuela": "VEN",
    "costa rica": "CRC", "honduras": "HON", "el salvador": "SLV", "algeria": "ALG",
    "morocco": "MAR", "egypt": "EGY", "nigeria": "NGA", "japan": "JPN", "south korea": "KOR",
    "australia": "AUS", "new zealand": "NZL", "wales": "WAL", "ireland": "IRL",
    "china": "CHN", "russia": "RUS", "india": "IND", "south africa": "RSA",
    "canada": "CAN", "guatemala": "GUA", "armenia": "ARM", "georgia": "GEO",
    "kazakhstan": "KAZ", "bosnia": "BIH", "finland": "FIN", "lithuania": "LTU",
    "latvia": "LVA", "albania": "ALB", "gibraltar": "GIB", "andorra": "AND",
}

# Club identity catalog: lowercase substring -> (Country, Code, PrimaryHex, SecondaryHex, TrimHex, CrestPattern)
CLUB_IDENTITY_CATALOG: dict[str, tuple[str, str, str, str, str, str]] = {
    "paris saint-germain": ("France", "FRA", "#004170", "#da291c", "#ffffff", "center_stripe"),
    "psg": ("France", "FRA", "#004170", "#da291c", "#ffffff", "center_stripe"),
    "barcelona": ("Spain", "ESP", "#a50044", "#004d98", "#edbb00", "stripes"),
    "real madrid": ("Spain", "ESP", "#ffffff", "#00529f", "#fece00", "emblem"),
    "atlético madrid": ("Spain", "ESP", "#cb3524", "#ffffff", "#272e61", "stripes"),
    "atletico madrid": ("Spain", "ESP", "#cb3524", "#ffffff", "#272e61", "stripes"),
    "villarreal": ("Spain", "ESP", "#facc15", "#005187", "#facc15", "emblem"),
    "real betis": ("Spain", "ESP", "#00954c", "#ffffff", "#ffd166", "stripes"),
    "athletic club": ("Spain", "ESP", "#ee2523", "#ffffff", "#111111", "stripes"),
    "real sociedad": ("Spain", "ESP", "#0067b1", "#ffffff", "#ffd166", "stripes"),
    "sevilla": ("Spain", "ESP", "#ffffff", "#d4021d", "#d4021d", "emblem"),
    "girona": ("Spain", "ESP", "#da291c", "#ffffff", "#ffd166", "stripes"),
    "fc porto": ("Portugal", "POR", "#00529f", "#ffffff", "#ffd166", "stripes"),
    "porto": ("Portugal", "POR", "#00529f", "#ffffff", "#ffd166", "stripes"),
    "sporting cp": ("Portugal", "POR", "#008057", "#ffffff", "#ffd166", "hoops"),
    "benfica": ("Portugal", "POR", "#e30613", "#ffffff", "#ffd166", "emblem"),
    "braga": ("Portugal", "POR", "#e30613", "#ffffff", "#ffd166", "sleeves"),
    "torreense": ("Portugal", "POR", "#00529f", "#da291c", "#ffffff", "halves"),
    "psv": ("Netherlands", "NED", "#ed1c24", "#ffffff", "#ffd166", "stripes"),
    "ajax": ("Netherlands", "NED", "#ffffff", "#d2122e", "#d2122e", "center_stripe"),
    "feyenoord": ("Netherlands", "NED", "#ed1c24", "#ffffff", "#111111", "halves"),
    "az alkmaar": ("Netherlands", "NED", "#db002c", "#ffffff", "#111111", "emblem"),
    "twente": ("Netherlands", "NED", "#e2001a", "#ffffff", "#ffffff", "emblem"),
    "liverpool": ("England", "ENG", "#c8102e", "#f6eb61", "#ffffff", "emblem"),
    "manchester city": ("England", "ENG", "#6cabdd", "#ffffff", "#1c2c5b", "emblem"),
    "man city": ("England", "ENG", "#6cabdd", "#ffffff", "#1c2c5b", "emblem"),
    "arsenal": ("England", "ENG", "#ef0107", "#ffffff", "#ffd166", "sleeves"),
    "chelsea": ("England", "ENG", "#034694", "#ffffff", "#dba111", "emblem"),
    "aston villa": ("England", "ENG", "#95bfe5", "#670e36", "#fee505", "sleeves"),
    "tottenham": ("England", "ENG", "#ffffff", "#132257", "#132257", "emblem"),
    "manchester united": ("England", "ENG", "#da291c", "#fbe122", "#ffffff", "emblem"),
    "newcastle": ("England", "ENG", "#241f20", "#ffffff", "#00b2a9", "stripes"),
    "bayern munich": ("Germany", "GER", "#dc052d", "#ffffff", "#0066b2", "emblem"),
    "borussia dortmund": ("Germany", "GER", "#fde100", "#111111", "#fde100", "emblem"),
    "dortmund": ("Germany", "GER", "#fde100", "#111111", "#fde100", "emblem"),
    "vfb stuttgart": ("Germany", "GER", "#ffffff", "#e32219", "#fde100", "hoops"),
    "stuttgart": ("Germany", "GER", "#ffffff", "#e32219", "#fde100", "hoops"),
    "bayer leverkusen": ("Germany", "GER", "#e32221", "#111111", "#fde100", "hoops"),
    "rb leipzig": ("Germany", "GER", "#ffffff", "#dd0741", "#001f47", "emblem"),
    "eintracht frankfurt": ("Germany", "GER", "#e1000f", "#111111", "#ffffff", "stripes"),
    "napoli": ("Italy", "ITA", "#008fd7", "#ffffff", "#003c82", "emblem"),
    "as roma": ("Italy", "ITA", "#970a2c", "#f0bc42", "#f0bc42", "halves"),
    "inter": ("Italy", "ITA", "#010e80", "#111111", "#c5a358", "stripes"),
    "ac milan": ("Italy", "ITA", "#fb090b", "#111111", "#ffffff", "stripes"),
    "juventus": ("Italy", "ITA", "#ffffff", "#111111", "#ffd166", "stripes"),
    "atalanta": ("Italy", "ITA", "#1e71b8", "#111111", "#ffffff", "stripes"),
    "bologna": ("Italy", "ITA", "#a21c26", "#1a2f48", "#ffffff", "stripes"),
    "lazio": ("Italy", "ITA", "#87d8f7", "#ffffff", "#ffd166", "emblem"),
    "fiorentina": ("Italy", "ITA", "#482e92", "#ffffff", "#ed1c24", "emblem"),
    "como": ("Italy", "ITA", "#0058a9", "#ffffff", "#0058a9", "emblem"),
    "lille": ("France", "FRA", "#e01e13", "#18203c", "#ffffff", "emblem"),
    "monaco": ("France", "FRA", "#e51b22", "#ffffff", "#ffd166", "sash"),
    "brest": ("France", "FRA", "#e30613", "#ffffff", "#e30613", "emblem"),
    "lens": ("France", "FRA", "#ec1c24", "#fff200", "#111111", "stripes"),
    "marseille": ("France", "FRA", "#ffffff", "#2faee0", "#ffd166", "emblem"),
    "lyon": ("France", "FRA", "#ffffff", "#da291c", "#14387f", "center_stripe"),
    "fenerbahce": ("Türkiye", "TUR", "#ffed00", "#002d72", "#ffffff", "stripes"),
    "galatasaray": ("Türkiye", "TUR", "#a90432", "#fdb912", "#fdb912", "halves"),
    "besiktas": ("Türkiye", "TUR", "#ffffff", "#111111", "#e30613", "stripes"),
    "slavia prague": ("Czechia", "CZE", "#e30613", "#ffffff", "#e30613", "halves"),
    "sparta prague": ("Czechia", "CZE", "#a6192e", "#ffffff", "#f0b323", "emblem"),
    "slovan bratislava": ("Slovakia", "SVK", "#5bc2e7", "#ffffff", "#003366", "emblem"),
    "sabah": ("Azerbaijan", "AZE", "#e83e8c", "#1e293b", "#ffffff", "emblem"),
    "qarabag": ("Azerbaijan", "AZE", "#1e293b", "#ffffff", "#ffd166", "emblem"),
    "aek athens": ("Greece", "GRE", "#facc15", "#111111", "#facc15", "stripes"),
    "olympiacos": ("Greece", "GRE", "#e30613", "#ffffff", "#ffd166", "stripes"),
    "paok": ("Greece", "GRE", "#ffffff", "#111111", "#ffffff", "stripes"),
    "panathinaikos": ("Greece", "GRE", "#007934", "#ffffff", "#ffd166", "emblem"),
    "bodo/glimt": ("Norway", "NOR", "#fcee33", "#111111", "#fcee33", "emblem"),
    "rosenborg": ("Norway", "NOR", "#ffffff", "#111111", "#d4af37", "emblem"),
    "brondby": ("Denmark", "DEN", "#ffed00", "#00469b", "#ffed00", "hoops"),
    "copenhagen": ("Denmark", "DEN", "#ffffff", "#0046ad", "#0046ad", "emblem"),
    "shakhtar donetsk": ("Ukraine", "UKR", "#f36c21", "#111111", "#ffffff", "stripes"),
    "dynamo kyiv": ("Ukraine", "UKR", "#ffffff", "#005bbb", "#ffd500", "sash"),
    "celtic": ("Scotland", "SCO", "#018749", "#ffffff", "#ffd166", "hoops"),
    "rangers": ("Scotland", "SCO", "#1b458f", "#ffffff", "#d40026", "emblem"),
    "club brugge": ("Belgium", "BEL", "#0072ce", "#111111", "#ffd166", "stripes"),
    "rb salzburg": ("Austria", "AUT", "#ffffff", "#dd0741", "#ffd166", "halves"),
    "sturm graz": ("Austria", "AUT", "#111111", "#ffffff", "#ffffff", "stripes"),
    "young boys": ("Switzerland", "SUI", "#ffed00", "#111111", "#ffed00", "hoops"),
    "dinamo zagreb": ("Croatia", "CRO", "#0047ab", "#ffffff", "#e30613", "emblem"),
    "red star": ("Serbia", "SRB", "#e30613", "#ffffff", "#ffd166", "stripes"),
    "vasco da gama": ("Brazil", "BRA", "#ffffff", "#111111", "#e30613", "sash"),
    "vasco": ("Brazil", "BRA", "#ffffff", "#111111", "#e30613", "sash"),
    "palmeiras": ("Brazil", "BRA", "#006437", "#ffffff", "#ffd166", "emblem"),
    "fluminense": ("Brazil", "BRA", "#8a1538", "#006341", "#ffffff", "stripes"),
    "flamengo": ("Brazil", "BRA", "#c52613", "#111111", "#ffffff", "hoops"),
    "atlético-mg": ("Brazil", "BRA", "#111111", "#ffffff", "#ffd166", "stripes"),
    "grêmio": ("Brazil", "BRA", "#0d80bf", "#111111", "#ffffff", "stripes"),
    "boca juniors": ("Argentina", "ARG", "#003399", "#ffcc00", "#ffcc00", "hoops"),
    "boca": ("Argentina", "ARG", "#003399", "#ffcc00", "#ffcc00", "hoops"),
    "river plate": ("Argentina", "ARG", "#ffffff", "#e30613", "#111111", "sash"),
    "racing": ("Argentina", "ARG", "#6cabdd", "#ffffff", "#ffd166", "stripes"),
    "colo colo": ("Chile", "CHI", "#ffffff", "#111111", "#e30613", "emblem"),
    "puerto montt": ("Chile", "CHI", "#008057", "#ffffff", "#00529f", "emblem"),
    "coquimbo": ("Chile", "CHI", "#facc15", "#111111", "#facc15", "stripes"),
    "unión la calera": ("Chile", "CHI", "#e30613", "#ffffff", "#e30613", "emblem"),
    "universidad de chile": ("Chile", "CHI", "#0046ad", "#e30613", "#ffffff", "emblem"),
    "antofagasta": ("Chile", "CHI", "#38bdf8", "#ffffff", "#0046ad", "stripes"),
    "montevideo city torque": ("Uruguay", "URU", "#6cabdd", "#ffffff", "#1c2c5b", "emblem"),
    "bolívar": ("Bolivia", "BOL", "#38bdf8", "#ffffff", "#0046ad", "emblem"),
    "the strongest": ("Bolivia", "BOL", "#facc15", "#111111", "#facc15", "stripes"),
    "always ready": ("Bolivia", "BOL", "#ffffff", "#e30613", "#111111", "sash"),
    "aurora": ("Bolivia", "BOL", "#38bdf8", "#ffffff", "#38bdf8", "emblem"),
    "independiente petrolero": ("Bolivia", "BOL", "#e30613", "#ffffff", "#e30613", "stripes"),
    "oriente petrolero": ("Bolivia", "BOL", "#00954c", "#ffffff", "#00954c", "emblem"),
    "nacional potosí": ("Bolivia", "BOL", "#ffffff", "#e30613", "#111111", "sash"),
    "real potosí": ("Bolivia", "BOL", "#7e22ce", "#ffffff", "#ffd166", "emblem"),
    "bournemouth": ("England", "ENG", "#da291c", "#111111", "#ffd166", "stripes"),
    "crystal palace": ("England", "ENG", "#1b458f", "#c4122e", "#ffffff", "stripes"),
    "c palace": ("England", "ENG", "#1b458f", "#c4122e", "#ffffff", "stripes"),
    "brighton": ("England", "ENG", "#0057b8", "#ffffff", "#facc15", "stripes"),
    "sunderland": ("England", "ENG", "#eb172b", "#ffffff", "#111111", "stripes"),
    "getafe": ("Spain", "ESP", "#005999", "#ffffff", "#da291c", "emblem"),
    "rennes": ("France", "FRA", "#e30613", "#111111", "#ffffff", "halves"),
    "stade rennais": ("France", "FRA", "#e30613", "#111111", "#ffffff", "halves"),
    "hoffenheim": ("Germany", "GER", "#1c63b7", "#ffffff", "#ffffff", "emblem"),
    "freiburg": ("Germany", "GER", "#e30613", "#111111", "#ffffff", "stripes"),
    "leverkusen": ("Germany", "GER", "#e32221", "#111111", "#fde100", "hoops"),
    "anderlecht": ("Belgium", "BEL", "#512d6d", "#ffffff", "#ffd166", "emblem"),
    "union sg": ("Belgium", "BEL", "#facc15", "#0046ad", "#facc15", "emblem"),
    "union st.-gilloise": ("Belgium", "BEL", "#facc15", "#0046ad", "#facc15", "emblem"),
    "kaa gent": ("Belgium", "BEL", "#0047ab", "#ffffff", "#ffffff", "emblem"),
    "sint-truidense": ("Belgium", "BEL", "#facc15", "#0046ad", "#facc15", "stripes"),
    "nec nijmegen": ("Netherlands", "NED", "#e30613", "#008057", "#111111", "halves"),
    "ferencvaros": ("Hungary", "HUN", "#008057", "#ffffff", "#ffd166", "stripes"),
    "viktoria plzen": ("Czechia", "CZE", "#e30613", "#0046ad", "#ffffff", "stripes"),
    "jablonec": ("Czechia", "CZE", "#008057", "#ffffff", "#ffffff", "emblem"),
    "jagiellonia": ("Poland", "POL", "#facc15", "#e30613", "#111111", "stripes"),
    "lech poznan": ("Poland", "POL", "#00529f", "#ffffff", "#ffffff", "emblem"),
    "omonia": ("Cyprus", "CYP", "#008057", "#ffffff", "#ffffff", "emblem"),
    "pafos": ("Cyprus", "CYP", "#00529f", "#ffffff", "#ffd166", "emblem"),
    "ararat-armenia": ("Armenia", "ARM", "#ffffff", "#e30613", "#111111", "emblem"),
    "lillestrom": ("Norway", "NOR", "#facc15", "#111111", "#facc15", "emblem"),
    "sk brann": ("Norway", "NOR", "#e30613", "#ffffff", "#ffffff", "emblem"),
    "midtjylland": ("Denmark", "DEN", "#111111", "#e30613", "#ffffff", "emblem"),
    "nordsjælland": ("Denmark", "DEN", "#e30613", "#facc15", "#e30613", "stripes"),
    "københavn": ("Denmark", "DEN", "#ffffff", "#0046ad", "#0046ad", "emblem"),
    "agf": ("Denmark", "DEN", "#ffffff", "#002d72", "#e30613", "emblem"),
    "hearts": ("Scotland", "SCO", "#8a1538", "#ffffff", "#ffffff", "emblem"),
    "trabzonspor": ("Türkiye", "TUR", "#8a1538", "#38bdf8", "#ffd166", "stripes"),
    "ofi crete": ("Greece", "GRE", "#111111", "#ffffff", "#ffffff", "stripes"),
    "nk celje": ("Slovenia", "SVN", "#facc15", "#0046ad", "#ffffff", "emblem"),
    "levski sofia": ("Bulgaria", "BUL", "#0046ad", "#ffffff", "#ffd166", "emblem"),
    "cska sofia": ("Bulgaria", "BUL", "#e30613", "#ffffff", "#ffd166", "emblem"),
    "fc lugano": ("Switzerland", "SUI", "#111111", "#ffffff", "#ffffff", "sash"),
    "fc thun": ("Switzerland", "SUI", "#e30613", "#ffffff", "#ffffff", "emblem"),
    "hajduk split": ("Croatia", "CRO", "#ffffff", "#0046ad", "#e30613", "emblem"),
    "estudiantes": ("Argentina", "ARG", "#e30613", "#ffffff", "#111111", "stripes"),
}


def sanitize_hex_color(raw: Any, default: str = "#38bdf8") -> str:
    """Validate and normalize a 6-digit hex color string; return default if malformed (e.g. ESPN '7755kk')."""
    s = str(raw or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            int(s, 16)
            return f"#{s.lower()}"
        except ValueError:
            pass
    return default


def enrich_team_identity(
    team: TeamInfo,
    category_name: str = "",
    venue_country: str = "",
) -> TeamInfo:
    """Populate club country, 3-letter code, jersey colors, and heraldic crest pattern."""
    team.color_primary = sanitize_hex_color(team.color_primary, "#374df5")
    team.color_secondary = sanitize_hex_color(team.color_secondary, "#ffffff")
    team.color_trim = sanitize_hex_color(team.color_trim, "#ffd166")

    nl = team.name.lower().strip()
    sl = team.short_name.lower().strip()

    for key, (country, code, c_pri, c_sec, c_trim, pattern) in CLUB_IDENTITY_CATALOG.items():
        if key == nl or key == sl or (len(key) >= 5 and (key in nl or key in sl)):
            if not team.country:
                team.country = country
            if not team.country_code:
                team.country_code = code
            team.color_primary = c_pri
            team.color_secondary = c_sec
            team.color_trim = c_trim
            team.crest_pattern = pattern
            break

    if not team.country:
        # Check if the team itself is a national / youth national team (e.g. 'Canada U17', 'Norway U17', 'China PR U17')
        cleaned_nat = nl
        for tok in (" u17", " u19", " u20", " u21", " u23", " women", " pr", " w"):
            if cleaned_nat.endswith(tok):
                cleaned_nat = cleaned_nat[: -len(tok)].strip()
        if cleaned_nat in COUNTRY_ALPHA3_MAP:
            team.country = cleaned_nat.title() if cleaned_nat != "usa" else "USA"
            team.country_code = COUNTRY_ALPHA3_MAP[cleaned_nat]
        elif sl in COUNTRY_ALPHA3_MAP:
            team.country = sl.title() if sl != "usa" else "USA"
            team.country_code = COUNTRY_ALPHA3_MAP[sl]

    continental_cats = {
        "europe", "south america", "north america", "asia", "africa",
        "world", "international", "concacaf", "football",
    }
    if not team.country:
        if category_name and category_name.lower() not in continental_cats:
            team.country = category_name
        elif venue_country and category_name.lower() not in ("world", "international"):
            team.country = venue_country

    if team.country and not team.country_code:
        team.country_code = COUNTRY_ALPHA3_MAP.get(team.country.lower(), team.country[:3].upper())

    if not team.crest_pattern:
        patterns = ("stripes", "emblem", "hoops", "halves", "center_stripe", "sash")
        team.crest_pattern = patterns[sum(ord(c) for c in team.name) % len(patterns)]

    if not team.color_trim:
        team.color_trim = "#ffd166"
    return team


TEAM_MANAGER_CATALOG: dict[str, str] = {
    # France / Ligue 1
    "paris saint-germain": "Luis Enrique",
    "paris saint germain": "Luis Enrique",
    "psg": "Luis Enrique",
    "marseille": "Roberto De Zerbi",
    "monaco": "Adi Hütter",
    "lille": "Bruno Génésio",
    "lyon": "Paulo Fonseca",
    "lens": "Will Still",
    "nice": "Franck Haise",
    "stade rennais": "Habib Beye",
    "rennes": "Habib Beye",
    "brest": "Éric Roy",
    "strasbourg": "Liam Rosenior",
    "toulouse": "Carles Martínez Novell",
    "nantes": "Antoine Kombouaré",
    # Spain / LaLiga
    "barcelona": "Hansi Flick",
    "real madrid": "Carlo Ancelotti",
    "atletico madrid": "Diego Simeone",
    "atlético madrid": "Diego Simeone",
    "villarreal": "Marcelino",
    "athletic club": "Ernesto Valverde",
    "real sociedad": "Imanol Alguacil",
    "real betis": "Manuel Pellegrini",
    "girona": "Míchel",
    "sevilla": "García Pimienta",
    "valencia": "Carlos Corberán",
    "celta vigo": "Claudio Giráldez",
    "osasuna": "Vicente Moreno",
    "mallorca": "Jagoba Arrasate",
    "getafe": "José Bordalás",
    "rayo vallecano": "Iñigo Pérez",
    "levante": "Julián Calero",
    # England / Premier League & EFL
    "manchester city": "Pep Guardiola",
    "liverpool": "Arne Slot",
    "arsenal": "Mikel Arteta",
    "chelsea": "Enzo Maresca",
    "manchester united": "Ruben Amorim",
    "tottenham": "Ange Postecoglou",
    "aston villa": "Unai Emery",
    "newcastle": "Eddie Howe",
    "brighton": "Fabian Hürzeler",
    "west ham": "Graham Potter",
    "fulham": "Marco Silva",
    "bournemouth": "Andoni Iraola",
    "crystal palace": "Oliver Glasner",
    "brentford": "Thomas Frank",
    "everton": "David Moyes",
    "nottingham forest": "Nuno Espírito Santo",
    "wolverhampton": "Vítor Pereira",
    "wolves": "Vítor Pereira",
    "leicester": "Ruud van Nistelrooy",
    "ipswich": "Kieran McKenna",
    "southampton": "Ivan Jurić",
    "leeds": "Daniel Farke",
    "burnley": "Scott Parker",
    "sunderland": "Régis Le Bris",
    "sheffield united": "Chris Wilder",
    "portsmouth": "John Mousinho",
    # Germany / Bundesliga
    "bayern munich": "Vincent Kompany",
    "borussia dortmund": "Niko Kovač",
    "dortmund": "Niko Kovač",
    "bayer leverkusen": "Xabi Alonso",
    "rb leipzig": "Marco Rose",
    "vfb stuttgart": "Sebastian Hoeneß",
    "stuttgart": "Sebastian Hoeneß",
    "eintracht frankfurt": "Dino Toppmöller",
    "freiburg": "Julian Schuster",
    "wolfsburg": "Ralph Hasenhüttl",
    "mainz": "Bo Henriksen",
    "borussia monchengladbach": "Gerardo Seoane",
    "werder bremen": "Ole Werner",
    "hoffenheim": "Christian Ilzer",
    "augsburg": "Jess Thorup",
    "union berlin": "Steffen Baumgart",
    # Italy / Serie A
    "internazionale": "Simone Inzaghi",
    "inter milan": "Simone Inzaghi",
    "ac milan": "Sérgio Conceição",
    "juventus": "Thiago Motta",
    "napoli": "Antonio Conte",
    "as roma": "Claudio Ranieri",
    "roma": "Claudio Ranieri",
    "atalanta": "Gian Piero Gasperini",
    "lazio": "Marco Baroni",
    "fiorentina": "Raffaele Palladino",
    "bologna": "Vincenzo Italiano",
    "torino": "Paolo Vanoli",
    "udinese": "Kosta Runjaić",
    "como": "Cesc Fàbregas",
    "genoa": "Patrick Vieira",
    # Portugal / Primeira Liga
    "sporting cp": "Rui Borges",
    "benfica": "Bruno Lage",
    "fc porto": "Martín Anselmi",
    "porto": "Martín Anselmi",
    "braga": "Carlos Carvalhal",
    "vitoria sc": "Luís Freire",
    "torreense": "Tiago Fernandes",
    # Netherlands / Belgium / Scotland / Rest of Europe
    "psv eindhoven": "Peter Bosz",
    "psv": "Peter Bosz",
    "feyenoord": "Robin van Persie",
    "ajax": "Francesco Farioli",
    "az alkmaar": "Maarten Martens",
    "twente": "Joseph Oosting",
    "nec nijmegen": "Rogier Meijer",
    "club brugge": "Nicky Hayen",
    "anderlecht": "David Hubert",
    "union st.-gilloise": "Sébastien Pocognoli",
    "genk": "Thorsten Fink",
    "celtic": "Brendan Rodgers",
    "rangers": "Barry Ferguson",
    "heart of midlothian": "Neil Critchley",
    "fenerbahce": "José Mourinho",
    "fenerbahçe": "José Mourinho",
    "galatasaray": "Okan Buruk",
    "besiktas": "Ole Gunnar Solskjær",
    "beşiktaş": "Ole Gunnar Solskjær",
    "trabzonspor": "Şenol Güneş",
    "slavia prague": "Jindřich Trpišovský",
    "sparta prague": "Lars Friis",
    "viktoria plzen": "Miroslav Koubek",
    "bodo/glimt": "Kjetil Knutsen",
    "bodø/glimt": "Kjetil Knutsen",
    "sk brann": "Freyr Alexandersson",
    "viking fk": "Bjarte Lunde Aarsheim",
    "lillestrom": "Hans Erik Ødegaard",
    "slovan bratislava": "Vladimír Weiss",
    "shakhtar donetsk": "Marino Pušić",
    "dinamo zagreb": "Fabio Cannavaro",
    "rb salzburg": "Thomas Letsch",
    "salzburg": "Thomas Letsch",
    "sturm graz": "Jürgen Säumel",
    "lask linz": "Markus Schopp",
    "young boys": "Giorgio Contini",
    "fc lugano": "Mattia Croci-Torti",
    "aek athens": "Matías Almeyda",
    "olympiacos": "José Luis Mendilibar",
    "panathinaikos": "Rui Vitória",
    "paok": "Răzvan Lucescu",
    "ofi crete": "Milan Rastavac",
    "ferencvaros": "Robbie Keane",
    "lech poznan": "Niels Frederiksen",
    "jagiellonia bialystok": "Adrian Siemieniec",
    "sabah fk": "Vasili Berezutski",
    "nk celje": "Albert Riera",
    "omonia nicosia": "Giannis Anastasiou",
    "pafos": "Juan Carlos Carcedo",
    "csu craiova": "Mirel Rădoi",
    # South America
    "flamengo": "Filipe Luís",
    "palmeiras": "Abel Ferreira",
    "botafogo": "Renato Paiva",
    "atletico-mg": "Cuca",
    "atlético-mg": "Cuca",
    "corinthians": "Ramón Díaz",
    "sao paulo": "Luis Zubeldía",
    "são paulo": "Luis Zubeldía",
    "vasco da gama": "Fábio Carille",
    "vasco": "Fábio Carille",
    "fluminense": "Mano Menezes",
    "gremio": "Gustavo Quinteros",
    "internacional": "Roger Machado",
    "cruzeiro": "Leonardo Jardim",
    "bahia": "Rogério Ceni",
    "fortaleza": "Juan Pablo Vojvoda",
    "boca juniors": "Fernando Gago",
    "river plate": "Marcelo Gallardo",
    "racing club": "Gustavo Costas",
    "independiente": "Julio Vaccari",
    "penarol": "Diego Aguirre",
    "peñarol": "Diego Aguirre",
    "nacional": "Martín Lasarte",
    "colo-colo": "Jorge Almirón",
    # Saudi Pro League / MLS / Liga MX / J1 League
    "al hilal": "Jorge Jesus",
    "al nassr": "Stefano Pioli",
    "al ittihad": "Laurent Blanc",
    "al ahli": "Matthias Jaissle",
    "al qadsiah": "Míchel",
    "al ettifaq": "Saad Al-Shehri",
    "al taawoun": "Mohammed Al-Abdali",
    "al riyadh": "Sabri Lamouchi",
    "inter miami": "Javier Mascherano",
    "la galaxy": "Greg Vanney",
    "lafc": "Steve Cherundolo",
    "fc cincinnati": "Pat Noonan",
    "d.c. united": "Troy Lesesne",
    "guadalajara": "Óscar García",
    "necaxa": "Nicolás Larcamón",
    "tigres uanl": "Veljko Paunović",
    "leon": "Eduardo Berizzo",
    "león": "Eduardo Berizzo",
    "club america": "André Jardine",
    "cruz azul": "Vicente Sánchez",
    "monterrey": "Martín Demichelis",
    "vissel kobe": "Takayuki Yoshida",
    "sanfrecce hiroshima": "Michael Skibbe",
    "machida zelvia": "Go Kuroda",
    "gamba osaka": "Dani Poyatos",
    "kashima antlers": "Toru Oniki",
    "urawa red diamonds": "Maciej Skorża",
    "kawasaki frontale": "Shigetoshi Hasebe",
    "yokohama f. marinos": "Steve Holland",
    "nagoya grampus": "Kenta Hasegawa",
    "cerezo osaka": "Arthur Papas",
    "fc tokyo": "Rikizo Matsuhashi",
    "kashiwa reysol": "Ricardo Rodríguez",
    # National Teams
    "argentina": "Lionel Scaloni",
    "brazil": "Dorival Júnior",
    "france": "Didier Deschamps",
    "spain": "Luis de la Fuente",
    "england": "Thomas Tuchel",
    "germany": "Julian Nagelsmann",
    "portugal": "Roberto Martínez",
    "italy": "Luciano Spalletti",
    "netherlands": "Ronald Koeman",
    "belgium": "Rudi Garcia",
    "croatia": "Zlatko Dalić",
    "colombia": "Néstor Lorenzo",
    "uruguay": "Marcelo Bielsa",
    "usa": "Mauricio Pochettino",
    "mexico": "Javier Aguirre",
    "canada": "Jesse Marsch",
    "norway": "Ståle Solbakken",
    "japan": "Hajime Moriyasu",
    "south korea": "Hong Myung-bo",
    "morocco": "Walid Regragui",
    "senegal": "Pape Thiaw",
    "nigeria": "Éric Chelle",
}


def resolve_team_manager(name: str, short_name: str = "") -> str:
    """Resolve the head coach / manager for a club or national team."""
    for candidate in (name.lower().strip(), short_name.lower().strip()):
        if not candidate:
            continue
        if candidate in TEAM_MANAGER_CATALOG:
            return TEAM_MANAGER_CATALOG[candidate]
        for key, mgr in TEAM_MANAGER_CATALOG.items():
            if len(key) >= 5 and (key in candidate or candidate in key):
                return mgr
    return ""



@dataclass
class TeamInfo:
    id: int
    name: str
    short_name: str
    name_code: str
    color_primary: str = "#374df5"
    color_secondary: str = "#ffffff"
    red_cards: int = 0
    country: str = ""
    country_code: str = ""
    crest_pattern: str = ""
    color_trim: str = "#ffd166"

    @property
    def country_display(self) -> str:
        if self.country_code and self.country:
            return f"{self.country_code} • {self.country}"
        return self.country or self.country_code

    @classmethod
    def from_dict(cls, data: dict[str, Any], red_cards: int = 0) -> TeamInfo:
        colors = data.get("teamColors") or {}
        c_raw = data.get("country") or {}
        c_name = str(c_raw.get("name") or "")
        c_code = str(c_raw.get("alpha3") or c_raw.get("alpha2") or "")
        if c_name and not c_code:
            c_code = COUNTRY_ALPHA3_MAP.get(c_name.lower(), c_name[:3].upper())
        t = cls(
            id=int(data.get("id") or 0),
            name=str(data.get("name") or "Unknown"),
            short_name=str(data.get("shortName") or data.get("name") or "Unknown"),
            name_code=str(data.get("nameCode") or (data.get("name") or "UNK")[:3].upper()),
            color_primary=str(colors.get("primary") or "#374df5"),
            color_secondary=str(colors.get("secondary") or "#ffffff"),
            red_cards=red_cards,
            country=c_name,
            country_code=c_code,
        )
        return enrich_team_identity(t)


@dataclass
class ScoreInfo:
    current: int | None = None
    display: int | None = None
    period1: int | None = None
    period2: int | None = None
    normaltime: int | None = None
    extra1: int | None = None
    extra2: int | None = None
    penalties: int | None = None
    aggregated: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ScoreInfo:
        if not data:
            return cls()
        return cls(
            current=data.get("current"),
            display=data.get("display"),
            period1=data.get("period1"),
            period2=data.get("period2"),
            normaltime=data.get("normaltime"),
            extra1=data.get("extra1"),
            extra2=data.get("extra2"),
            penalties=data.get("penalties"),
            aggregated=data.get("aggregated"),
        )


@dataclass
class TournamentInfo:
    id: int
    unique_id: int
    name: str
    category_id: int
    category_name: str
    season_id: int
    round_info: str = ""
    priority: int = 0

    @property
    def display_title(self) -> str:
        base = f"{self.category_name} • {self.name}"
        if self.round_info:
            return f"{base} ({self.round_info})"
        return base


TOP_UNIQUE_TOURNAMENT_PRIORITY: dict[int, int] = {
    7: 1000,     # UEFA Champions League
    679: 960,    # UEFA Europa League
    17015: 940,  # UEFA Conference League
    17: 920,     # Premier League
    8: 900,      # LaLiga
    23: 890,     # Serie A
    35: 880,     # Bundesliga
    34: 870,     # Ligue 1
    238: 860,    # Liga Portugal Betclic
    37: 840,     # Eredivisie
    325: 830,    # Brasileirão Série A
    384: 825,    # CONMEBOL Libertadores
    480: 815,    # CONMEBOL Sudamericana
    19: 810,     # FA Cup
    21: 805,     # EFL Cup
    329: 800,    # Copa del Rey
    328: 795,    # Coppa Italia
    217: 790,    # DFB-Pokal
    240: 785,    # Taça de Portugal
    18: 770,     # Championship
    52: 760,     # Trendyol Süper Lig
    955: 750,    # Saudi Pro League
    242: 740,    # MLS
    155: 730,    # Liga Profesional Argentina
    2132: 720,   # UEFA Youth League
    1054: 710,   # CAF Champions League
}


@dataclass
class MatchEvent:
    id: int
    slug: str
    start_timestamp: int
    status_type: str        # "inprogress", "finished", "notstarted", "postponed", "canceled"
    status_description: str # "1st half", "Halftime", "2nd half", "Ended", "Not started", "AP", "AET"
    status_code: int
    home_team: TeamInfo
    away_team: TeamInfo
    home_score: ScoreInfo
    away_score: ScoreInfo
    tournament: TournamentInfo
    current_period_start: int | None = None
    injury_time_1: int = 0
    injury_time_2: int = 0
    winner_code: int = 0
    venue_name: str = ""
    venue_city: str = ""
    venue_country: str = ""
    referee_name: str = ""
    referee_country: str = ""
    leg_info: str = ""
    prev_leg_score: str = ""
    series_note: str = ""
    attendance: int | None = None
    has_xg: bool = False
    has_graph: bool = False
    has_lineups: bool = False
    home_manager: str = ""
    away_manager: str = ""

    @property
    def is_live(self) -> bool:
        return self.status_type == "inprogress"

    @property
    def is_finished(self) -> bool:
        return self.status_type == "finished"

    @property
    def is_upcoming(self) -> bool:
        return self.status_type == "notstarted"

    def live_minute_str(self, now_ts: float) -> str:
        """Compute the live match minute string just like SofaScore."""
        if self.status_type == "finished":
            if self.status_code == 120 or "AP" in self.status_description:
                return "PEN"
            if self.status_code == 110 or "AET" in self.status_description:
                return "AET"
            return "FT"
        if self.status_type == "postponed":
            return "POST"
        if self.status_type == "canceled":
            return "CANC"
        if self.status_type != "inprogress":
            import datetime
            dt = datetime.datetime.fromtimestamp(self.start_timestamp)
            return dt.strftime("%H:%M")

        desc_lower = self.status_description.lower()
        if "halftime" in desc_lower or self.status_code == 31:
            return "HT"
        if "pause" in desc_lower or "break" in desc_lower:
            return "BRK"
        if "penalt" in desc_lower or self.status_code == 50:
            return "PEN"

        if self.current_period_start:
            elapsed_min = max(1, int((now_ts - self.current_period_start) // 60) + 1)
            if self.status_code == 6 or "1st" in desc_lower:
                if elapsed_min > 45:
                    return f"45+{elapsed_min - 45}'"
                return f"{elapsed_min}'"
            if self.status_code == 7 or "2nd" in desc_lower:
                minute = 45 + elapsed_min
                if minute > 90:
                    return f"90+{minute - 90}'"
                return f"{minute}'"
            if "extra" in desc_lower:
                base = 90 if "1st" in desc_lower else 105
                return f"{base + elapsed_min}'"
            return f"{elapsed_min}'"
        return self.status_description[:6]

    @classmethod
    def from_dict(cls, ev: dict[str, Any]) -> MatchEvent:
        status = ev.get("status") or {}
        t_raw = ev.get("tournament") or {}
        ut_raw = t_raw.get("uniqueTournament") or {}
        cat_raw = t_raw.get("category") or {}
        season_raw = ev.get("season") or {}
        round_raw = ev.get("roundInfo") or {}
        time_raw = ev.get("time") or {}
        venue_raw = ev.get("venue") or {}
        ref_raw = ev.get("referee") or {}

        ut_id = int(ut_raw.get("id") or t_raw.get("id") or 0)
        cat_prio = int(cat_raw.get("priority") or 0)
        t_prio = TOP_UNIQUE_TOURNAMENT_PRIORITY.get(ut_id, int(t_raw.get("priority") or 0) + cat_prio * 2)

        round_str = ""
        if round_raw.get("name"):
            round_str = str(round_raw["name"])
        elif round_raw.get("round"):
            round_str = f"R{round_raw['round']}"

        tournament = TournamentInfo(
            id=int(t_raw.get("id") or 0),
            unique_id=ut_id,
            name=str(ut_raw.get("name") or t_raw.get("name") or "League"),
            category_id=int(cat_raw.get("id") or 0),
            category_name=str(cat_raw.get("name") or "World"),
            season_id=int(season_raw.get("id") or 0),
            round_info=round_str,
            priority=t_prio,
        )

        home_red = int(ev.get("homeRedCards") or 0)
        away_red = int(ev.get("awayRedCards") or 0)

        venue_city = ""
        if isinstance(venue_raw.get("city"), dict):
            venue_city = str(venue_raw["city"].get("name") or "")
        venue_country = ""
        if isinstance(venue_raw.get("country"), dict):
            venue_country = str(venue_raw["country"].get("name") or "")
        venue_stadium = ""
        if isinstance(venue_raw.get("stadium"), dict):
            venue_stadium = str(venue_raw["stadium"].get("name") or "")
        elif venue_raw.get("name"):
            venue_stadium = str(venue_raw.get("name") or "")

        ref_country = ""
        if isinstance(ref_raw.get("country"), dict):
            ref_country = str(
                ref_raw["country"].get("alpha3")
                or ref_raw["country"].get("alpha2")
                or ref_raw["country"].get("name")
                or ""
            )

        home_team = TeamInfo.from_dict(ev.get("homeTeam") or {}, red_cards=home_red)
        away_team = TeamInfo.from_dict(ev.get("awayTeam") or {}, red_cards=away_red)
        enrich_team_identity(home_team, tournament.category_name, venue_country)
        enrich_team_identity(away_team, tournament.category_name)

        home_score = ScoreInfo.from_dict(ev.get("homeScore"))
        away_score = ScoreInfo.from_dict(ev.get("awayScore"))
        leg_info = ""
        prev_leg_score = ""
        if home_score.aggregated is not None and away_score.aggregated is not None:
            leg_info = "2nd Leg"
            if home_score.current is not None and away_score.current is not None:
                p_home = home_score.aggregated - home_score.current
                p_away = away_score.aggregated - away_score.current
                if p_home >= 0 and p_away >= 0:
                    prev_leg_score = f"1st Leg: {p_home} - {p_away}"
        elif ev.get("previousLegEventId"):
            leg_info = "2nd Leg"

        return cls(
            id=int(ev.get("id") or 0),
            slug=str(ev.get("slug") or ""),
            start_timestamp=int(ev.get("startTimestamp") or 0),
            status_type=str(status.get("type") or "notstarted"),
            status_description=str(status.get("description") or ""),
            status_code=int(status.get("code") or 0),
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            tournament=tournament,
            current_period_start=time_raw.get("currentPeriodStartTimestamp"),
            injury_time_1=int(time_raw.get("injuryTime1") or 0),
            injury_time_2=int(time_raw.get("injuryTime2") or 0),
            winner_code=int(ev.get("winnerCode") or 0),
            venue_name=venue_stadium,
            venue_city=venue_city,
            venue_country=venue_country,
            referee_name=str(ref_raw.get("name") or ""),
            referee_country=ref_country,
            leg_info=leg_info,
            prev_leg_score=prev_leg_score,
            attendance=ev.get("attendance"),
            has_xg=bool(ev.get("hasXg")),
            has_graph=bool(ev.get("hasEventPlayerHeatMap") or ev.get("hasGlobalHighlights")),
            has_lineups=bool(ev.get("hasEventPlayerStatistics")),
            home_manager=str(
                (ev.get("homeTeam") or {}).get("manager", {}).get("name")
                or resolve_team_manager(home_team.name, home_team.short_name)
            ),
            away_manager=str(
                (ev.get("awayTeam") or {}).get("manager", {}).get("name")
                or resolve_team_manager(away_team.name, away_team.short_name)
            ),
        )


@dataclass
class IncidentItem:
    incident_type: str   # "goal", "card", "substitution", "period", "injuryTime", "varDecision", "inGamePenalty"
    incident_class: str  # "regular", "penalty", "ownGoal", "yellow", "red", "yellowRed", etc.
    time: int
    added_time: int = 0
    is_home: bool | None = None
    player_name: str = ""
    player_short: str = ""
    assist_name: str = ""
    player_in_name: str = ""
    player_out_name: str = ""
    home_score: int | None = None
    away_score: int | None = None
    reason: str = ""
    text: str = ""
    length: int = 0
    xg: float | None = None

    @property
    def minute_label(self) -> str:
        if self.time < 0:
            return "-"
        if self.added_time and self.added_time > 0:
            return f"{self.time}+{self.added_time}'"
        return f"{self.time}'"

    @property
    def is_injury_sub(self) -> bool:
        if self.incident_type != "substitution":
            return False
        return (
            "injur" in self.incident_class.lower()
            or "injur" in self.reason.lower()
            or "injur" in self.text.lower()
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> IncidentItem:
        itype = str(raw.get("incidentType") or "")
        iclass = str(raw.get("incidentClass") or "")
        reason_str = str(raw.get("reason") or "")
        if itype == "substitution" and (
            raw.get("injury") is True
            or "injur" in iclass.lower()
            or "injur" in reason_str.lower()
        ):
            iclass = "injury"
        player = raw.get("player") or {}
        assist1 = raw.get("assist1") or {}
        player_in = raw.get("playerIn") or {}
        player_out = raw.get("playerOut") or {}

        xg_val: float | None = None
        for act in raw.get("footballPassingNetworkAction") or []:
            if act.get("eventType") == "goal" and act.get("xg") is not None:
                try:
                    xg_val = float(act["xg"])
                except (TypeError, ValueError):
                    pass

        return cls(
            incident_type=itype,
            incident_class=iclass,
            time=int(raw.get("time") or 0),
            added_time=int(raw.get("addedTime") or 0),
            is_home=raw.get("isHome"),
            player_name=str(player.get("name") or raw.get("playerName") or ""),
            player_short=str(player.get("shortName") or player.get("name") or ""),
            assist_name=str(assist1.get("shortName") or assist1.get("name") or ""),
            player_in_name=str(player_in.get("shortName") or player_in.get("name") or ""),
            player_out_name=str(player_out.get("shortName") or player_out.get("name") or ""),
            home_score=raw.get("homeScore"),
            away_score=raw.get("awayScore"),
            reason=str(raw.get("reason") or ""),
            text=str(raw.get("text") or ""),
            length=int(raw.get("length") or 0),
            xg=xg_val,
        )


@dataclass
class StatItem:
    key: str
    name: str
    home_str: str
    away_str: str
    home_val: float
    away_val: float
    compare_code: int  # 1 = home better, 2 = away better, 3 = equal
    statistics_type: str = "positive"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> StatItem:
        return cls(
            key=str(raw.get("key") or ""),
            name=str(raw.get("name") or ""),
            home_str=str(raw.get("home") or "0"),
            away_str=str(raw.get("away") or "0"),
            home_val=float(raw.get("homeValue") or 0.0),
            away_val=float(raw.get("awayValue") or 0.0),
            compare_code=int(raw.get("compareCode") or 3),
            statistics_type=str(raw.get("statisticsType") or "positive"),
        )


@dataclass
class StatGroup:
    group_name: str
    items: list[StatItem] = field(default_factory=list)


@dataclass
class PeriodStats:
    period: str  # "ALL", "1ST", "2ND"
    groups: list[StatGroup] = field(default_factory=list)


@dataclass
class CommentItem:
    id: int
    type: str
    text: str
    time: int
    added_time: int = 0
    is_home: bool | None = None
    player_name: str = ""

    @property
    def minute_label(self) -> str:
        if self.time <= 0:
            return "•"
        if self.added_time and self.added_time > 0:
            return f"{self.time}+{self.added_time}'"
        return f"{self.time}'"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CommentItem:
        player = raw.get("player") or {}
        return cls(
            id=int(raw.get("id") or 0),
            type=str(raw.get("type") or "comment"),
            text=str(raw.get("text") or ""),
            time=int(raw.get("time") or 0),
            added_time=int(raw.get("addedTime") or 0),
            is_home=raw.get("isHome"),
            player_name=str(player.get("shortName") or player.get("name") or ""),
        )


@dataclass
class PlayerLineup:
    id: int
    name: str
    short_name: str
    shirt_number: str
    position: str
    substitute: bool
    captain: bool
    rating: float | None
    minutes_played: int
    goals: int
    assists: int
    yellow_cards: int = 0
    red_cards: int = 0
    subbed_in: int | None = None
    subbed_out: int | None = None
    subbed_out_injured: bool = False
    stats: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PlayerLineup:
        p = raw.get("player") or {}
        st = raw.get("statistics") or {}
        rating_raw = st.get("rating") or raw.get("avgRating")
        rating = float(rating_raw) if rating_raw is not None else None
        return cls(
            id=int(p.get("id") or 0),
            name=str(p.get("name") or "Unknown"),
            short_name=str(p.get("shortName") or p.get("name") or "Unknown"),
            shirt_number=str(raw.get("shirtNumber") or raw.get("jerseyNumber") or p.get("jerseyNumber") or "-"),
            position=str(raw.get("position") or p.get("position") or "-"),
            substitute=bool(raw.get("substitute")),
            captain=bool(raw.get("captain")),
            rating=rating,
            minutes_played=int(st.get("minutesPlayed") or 0),
            goals=int(st.get("goals") or 0),
            assists=int(st.get("goalAssist") or 0),
            subbed_out_injured=bool(raw.get("subbedOutInjured") or st.get("subbedOutInjured")),
            stats=st,
        )


@dataclass
class MissingPlayer:
    name: str
    short_name: str
    reason: str
    status_type: str  # "missing", "doubtful"


@dataclass
class TeamLineup:
    formation: str = ""
    players: list[PlayerLineup] = field(default_factory=list)
    missing_players: list[MissingPlayer] = field(default_factory=list)

    @property
    def starters(self) -> list[PlayerLineup]:
        return [p for p in self.players if not p.substitute]

    @property
    def substitutes(self) -> list[PlayerLineup]:
        return [p for p in self.players if p.substitute]


@dataclass
class MatchLineups:
    confirmed: bool = False
    home: TeamLineup = field(default_factory=TeamLineup)
    away: TeamLineup = field(default_factory=TeamLineup)


@dataclass
class MomentumPoint:
    minute: float
    value: float  # > 0 means Home attacking momentum, < 0 means Away attacking momentum


@dataclass
class StandingRow:
    position: int
    team_id: int
    team_name: str
    team_short: str
    matches: int
    wins: int
    draws: int
    losses: int
    scores_for: int
    scores_against: int
    score_diff: str
    points: int
    promotion_text: str = ""


@dataclass
class H2HInfo:
    home_wins: int = 0
    draws: int = 0
    away_wins: int = 0
    home_form: list[str] = field(default_factory=list)
    away_form: list[str] = field(default_factory=list)
    home_avg_rating: str = ""
    away_avg_rating: str = ""
    home_position: int | None = None
    away_position: int | None = None
    home_points: str = ""
    away_points: str = ""


@dataclass
class FullMatchBundle:
    event: MatchEvent
    incidents: list[IncidentItem] = field(default_factory=list)
    statistics: list[PeriodStats] = field(default_factory=list)
    comments: list[CommentItem] = field(default_factory=list)
    lineups: MatchLineups | None = None
    momentum: list[MomentumPoint] = field(default_factory=list)
    standings: list[StandingRow] = field(default_factory=list)
    standings_name: str = ""
    h2h: H2HInfo = field(default_factory=H2HInfo)
