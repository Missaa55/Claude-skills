# Použití Builderů a obrázků v Claude

## Realistické obrázky na běžném počítači

Samostatný balíček `claude-image-studio-0.2.0.zip` obsahuje skill pro Claude,
instrukce pro připojený generátor, kontrolu výsledků a volitelné pomocné skripty.
Není nutné instalovat celý WebBuilder. Samotný skill neobsahuje obrazový model.
Claude připraví zadání, zavolá připojený nástroj, zkontroluje skutečný obrázek
a přizpůsobí jej webu. Výkonná místní grafická karta ani placené OpenAI API nejsou
podmínkou vzdálené cesty. Internet, účet a dostupná bezplatná kvóta poskytovatele ano.

1. Stáhněte balíček z artefaktu `standalone-builders` u příslušného ověřeného
   [běhu Actions](VERIFICATION.md). Porovnejte SHA-256 s přiloženým součtem.
2. V Claude povolte vytváření souborů a otevřete **Customize → Skills → + →
   Create skill → Upload a skill**. Nahrajte ZIP a skill zapněte. Jde o aktuální
   [postup Anthropic](https://support.claude.com/en/articles/12512180-use-skills-in-claude),
   jeho dostupnost může omezovat správce organizace.
3. Přihlaste se do [Hugging Face MCP settings](https://huggingface.co/settings/mcp)
   a postupujte podle konfigurace pro váš Claude klient. Připojení účtu schvalujete
   vy; neposílejte hesla ani tokeny do chatu nebo repozitáře.
4. Přidejte vhodný generátor s MCP značkou do Spaces Tools; případně povolte
   **Dynamic Spaces**, aby jej Claude mohl vyhledat sám. Musí být dostupný pro váš
   účet, mít vhodnou licenci a vejít se do bezplatné kvóty. Podrobnosti a zdroje
   jsou v [providers.md](../WebBuilder/skills/claude-image-studio/references/providers.md).
5. V nové konverzaci požádejte například:

   > Použij claude-image-studio. Vygeneruj realistickou ilustrační fotografii
   > fiktivního elektrikáře v dílně pro web elektro firmy. Přirozené denní světlo,
   > tmavomodré pracovní oblečení, zavřený rozvaděč bez práce pod napětím,
   > osoba vpravo a volné místo pro nadpis vlevo, formát 3:2. Použij pouze
   > dostupnou bezplatnou kvótu. Zkontroluj ruce, nářadí a skutečný výstupní soubor.
   > Ulož obrázek a údaje o použitém nástroji. Nevydávej osobu za skutečného zaměstnance.

Bez připojeného generátoru Claude nevytvoří realistickou fotografii jen instalací
skill souboru. Při vyčerpané kvótě skill zastaví generování a vysvětlí důvod.
Nekupuje kredity ani automaticky nestahuje velké modely. Přihlášené generování přes
Claude/HF je v této práci **NOT VERIFIED**; ověření formátu a pomocných skriptů je
vedeno odděleně. Ukázková fotografie z ChatGPT nepotvrzuje tuto integraci.

Pro Claude Code lze skill rozbalit do nové složky `~/.claude/skills/claude-image-studio`.
Po přihlášení podle HF průvodce lze použít jeho dokumentovaný příkaz:

```text
claude mcp add --transport http hf-images "https://huggingface.co/mcp?login"
```

Blender je volitelný pro vlastní 3D objekty a materiály; aplikace není přibalena.
Inkscape pomůže s editovatelnými SVG a Krita s malbou/maskami. ComfyUI je pokročilá
volitelná místní cesta s vlastními nároky na model a hardware. Pro realistického
člověka zůstává výchozí připojený generátor. CC0 zdroje ověřujte u konkrétního assetu,
nikoli podle náhledu vyhledávače.

## Instalace samostatného Builderu

Pro příkazy je nutný Python 3.11+. V repozitáři přepněte na větev
`codex/builders-runtime-qa`, protože změny zatím nejsou sloučeny do `main`.
Začněte testovací složkou:

```bash
python -m distribution.cli install web --target ../moje-skills
python -m distribution.cli status --target ../moje-skills
```

Místo `web` lze použít `app` nebo `minecraft`; stejné příkazy postupně nainstalují
libovolnou kombinaci. Bez `--target` se použije `~/.claude/skills`, s `--client codex`
adresář `~/.agents/skills`. Složky s vlastními úpravami instalátor nepřepíše.
Každý modul obsahuje vlastní runtime a Cleaner a nepotřebuje ostatní Buildery.
Samostatné ZIP balíčky se nejprve rozbalí do nové složky a ověří příkazem
`python -m distribution.bundle verify .` spuštěným uvnitř balíčku.

```bash
python -m distribution.cli update web --target ../moje-skills
python -m distribution.cli uninstall web --target ../moje-skills
```

Odinstalace odstraní pouze zaznamenané nezměněné soubory. Cizí data zůstávají.
Při konfliktu nejprve zálohujte vlastní úpravy a porovnejte je; nemažte stavové
soubory ani zámky naslepo. Obnovu přerušené transakce popisuje
[distribuční příručka](../distribution/README.md).

## Spuštění referenčního webu a aplikace

Z kořene repozitáře vytvořte nový projekt. Cílová složka ještě nesmí existovat.
`create` je deterministická referenční generace ze zadání, nikoli běh AI agenta.

```bash
python -m core.builder_cli create --spec examples/briefs/web.json --workspace ../elektro-web
python -m core.builder_cli check web --workspace ../elektro-web --execute --trusted-local
python ../elektro-web/server.py --port 8080
```

Otevřete `http://127.0.0.1:8080`. Formulář ukládá pouze testovací poptávky,
nikomu neposílá e-mail. Pro aplikaci:

```bash
python -m core.builder_cli create --spec examples/briefs/app.json --workspace ../elektro-app
python -m core.builder_cli check app --workspace ../elektro-app --execute --trusted-local
python ../elektro-app/server.py init --demo
python ../elektro-app/server.py serve --port 8787
```

Inicializace vypíše nově vygenerované demo přihlašovací údaje pouze lokálně.
Otevřete `http://127.0.0.1:8787` a používejte výhradně syntetická data.
`--trusted-local` výslovně spouští zkontrolovaný zdroj na hostiteli; není to sandbox.
U neznámých projektů tuto volbu nepoužívejte. Oba servery ukončíte Ctrl+C.

Průzkum dvaceti skutečně dostupných domén a dva rozdílné směry ukazuje
[příručka designeru](DESIGNER.md). Volba fontů používá individuálně zvolené systémové
stacky; automatické licencování a párování vlastních fontových souborů není hotové.

## Minecraft a autonomní agent

Minecraft reference vyžaduje Java 21 a Gradle 8.14.3. Nový Fabric projekt vytvoří
`create` s `examples/briefs/minecraft.json`; ve vzniklém adresáři spusťte
`gradle --no-daemon build`. Produkční JAR je v `build/libs/`.
Test skutečného serveru smí běžet jen po přijetí Minecraft EULA v odděleném světě.
Výsledky Fabric/Paper/NeoForge/datapacků jsou rozlišeny v předávací zprávě.

Pro autonomní `run` je nutný dostupný přihlášený Claude Code nebo Codex CLI a
předem připravený izolovaný kontejner s pevně určeným digestem. Výchozí režim při
chybějícím Dockeru bezpečně odmítne běh. Skill ani runtime přihlašovací údaje
neposkytují. Současný příkaz používá offline kontejner bez řešení pro bezpečné
přihlášení a síťový přístup k poskytovateli; samotná instalace Dockeru tedy nestačí.
Tuto část je ještě nutné implementovat a ověřit. Samostatný image skill využívá
přímo připojené nástroje v Claude a není na této kontejnerové cestě závislý.
Úplná AI cesta zůstává **NOT VERIFIED**; nepovažujte referenční
projekt za důkaz libovolného generování z přirozeného jazyka.
