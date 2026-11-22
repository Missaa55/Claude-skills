# Návrhář: průzkum oboru a dva odlišné směry

Implementované profily: **elektroinstalační služby** a **obuv / ukázkový katalog**.
Jde o parametrizované deterministické návrhy. Volné generování libovolné značky skutečným
Claude/Codex agentem zůstává **NOT VERIFIED**. Obuv nemá skutečný checkout ani platby.

## Postup

```bash
python -m core.builder_cli research --candidates examples/research/electrical-candidates.json --output electrical-research.json
python -m core.builder_cli design --industry electrical --name "Jistič Elektro" --task "Web elektro firmy s přehledným postupem realizace" --research electrical-research.json --workspace ../elektro-navrhy
python -m core.builder_cli check web --workspace ../elektro-navrhy/a --execute --trusted-local
python -m core.builder_cli check web --workspace ../elektro-navrhy/b --execute --trusted-local
```

Pro obuv použijte `footwear-candidates.json` a `--industry footwear`. Každý návrh je
samostatně spustitelný: `python ../elektro-navrhy/a/server.py --port 8081`, druhý na portu 8082.
Před spuštěním je nutné vytvořit produkční výstup příkazem `check` nebo místním `python build.py`.
Příkazy spouštějte nad zkontrolovanými šablonami; `--trusted-local` není sandbox.

Průzkum přijímá 20–40 různých domén a vyžaduje nejméně **20 úspěšně načtených kandidátů**.
Měří dostupné HTML/CSS signály, fontové rodiny, mřížky, sticky prvky a deklarované animace.
Ukládá čas, URL, hashe zdrojů, omezení a chyby. Nespouští cizí JavaScript, nestahuje fonty
a nepřebírá fotografie, texty ani CSS. TLS chyby ani blokace neobchází. Celkový běh každého
kandidáta je omezen na 30 sekund v samostatném procesu; pracují nejvýše čtyři procesy současně.

Nedostupné kandidáty lze nahradit dalšími relevantními primárními weby. Nezapočítávají se
do počtu analyzovaných webů. Návrh odmítne jiný obor, méně než 20 domén, nedůvěryhodný
záznam nebo podklady starší než sedm dní. CI používá výslovně označené simulované průzkumy,
aby testy nezávisely na neustále se měnících cizích webech.

## Odlišnost a typografie

`design-comparison.json` porovnává sedm vlastností: typografickou kategorii, paletu,
úvodní kompozici, strukturu obsahu, povrchy, grafický jazyk a skrolování. Nejméně pět
musí být odlišných. První směr zohledňuje zjištěné fontové/mřížkové vzory a oborovou
srozumitelnost. Druhý volí opačný typografický charakter, odlišnou paletu, kompozici
a vlastní grafickou metaforu. Nejde o kopii konkrétního konkurenta.

Fonty se vybírají z ověřených systémových rodin podle oboru, značky a zadání; každý směr
má vlastní zásobník a fallbacky včetně českých znaků. To nezaručuje unikátní font pro každý
web na světě. Vlastní licencované WOFF2 fonty a jejich automatické vizuální párování zatím
nejsou implementovány. Změna fontu nevyžaduje externí sledovací službu ani novou závislost.

## Skrolování a životnost

`--scroll auto` použije příběhový sticky blok pro portfolio, postup či příběh produktu.
Pro rychlé získání kontaktu zůstane běžné skrolování. `off` jej vypne, `story` jej výslovně
vyžádá. Nikdy se neblokuje kolečko, dotyk ani klávesnice. Obsah zůstává přístupný bez
animací; `prefers-reduced-motion` má statickou variantu. QA testuje oba režimy.

Tříletý horizont znamená záměr dobře stárnoucího návrhu: čitelnost, kontrast, přehledná
hierarchie, responzivita, malý objem dat a nezávislost na krátkodobých efektech. Budoucí
vkus nelze doložit. Jeden průzkum popisuje současný vzorek, nikoliv rostoucí popularitu.
`research --previous old.json` porovná stejné domény ve dvou časově oddělených snímcích;
ani tato změna nedokazuje reprezentativní tržní trend nebo budoucí vývoj.

## Skutečné výsledky této práce

Elektro: 32 oslovených, 22 úspěšně analyzovaných domén. Obuv: 40 oslovených, 20 úspěšných.
Průzkum je **STATIC CHECK**, síťové načtení úspěšných zdrojů **REAL VERIFIED**; vizuální
hodnocení všech cizích webů **NOT VERIFIED**. Oba směry v obou oborech mají skutečné
produkční buildy, HTTP testy, desktopové/mobilní screenshoty, nulové automatické nálezy axe
v testovaných stavech a ověřenou odlišnost fontů/kompozice. Viz [předávací důkazy](VERIFICATION.md).
