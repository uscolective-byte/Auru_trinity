# Pamäť Trinity

## Hranica medzi kontextom a trvalou pamäťou

**Krátkodobý kontext** slúži iba na vykonanie aktuálnej relácie (napríklad rozpracovaný
krok alebo posledná voľba). Má identifikátor relácie a štandardne pravidlo `session`.
Ukončenie relácie ho odstráni. Do **dlhodobej používateľskej pamäte** sa údaj dostane
iba vtedy, keď je užitočný naprieč reláciami a používateľ jeho uloženie očakáva alebo
schválil. Projektové fakty patria projektu, nie globálnemu profilu používateľa.
Auditná udalosť opisuje operáciu; nesmie kopírovať jej citlivý obsah.

Modely sú oddelené, no každý záznam povinne nesie vlastníka, zdroj, UTC čas vzniku,
klasifikáciu citlivosti (`public`, `internal`, `confidential`, `restricted`) a pravidlo
retencie. Čítanie, export aj mazanie vyžadujú práve jeden rozsah: používateľa alebo
projekt. Aplikácia musí pred projektovým dopytom overiť členstvo používateľa; úložisko
potom technicky zabráni dopytu bez rozsahu.

## Životný cyklus a retencia

1. Pred zápisom sa určí účel, vlastník/projekt, zdroj, citlivosť a retencia. Heslá,
   API tokeny, prístupové tajomstvá ani celé hodnoty systémových premenných sa
   neukladajú. Implementácia odmietne payload s typickými názvami takýchto polí;
   volajúci má uložiť nanajvýš referenciu na správcu tajomstiev.
2. SQLite MVP uloží JSON payload a metadáta. Izoláciu zabezpečujú parametrizované
   používateľské alebo projektové filtre pri každom čítaní.
3. `session` trvá do explicitného ukončenia relácie. `30_days` a `365_days` sa počítajú
   od `created_at` a expirované záznamy sa pred operáciami fyzicky prečistia.
   `indefinite` znamená bez automatického termínu, nie zákaz vymazania; používa sa iba
   pri zdokumentovanom dôvode.
4. Export vráti iba neexpirované dáta vo zvolenom rozsahu spolu s metadátami, aby bol
   prenos a kontrola transparentná.
5. Po uplynutí retencie alebo oprávnenej požiadavke sa záznam fyzicky odstráni.

## Export a odstránenie používateľských dát

Pre požiadavku dotknutej osoby najprv autentizujte žiadateľa. Zavolajte
`export(user_id=...)` pre strojovo čitateľný export a následne
`delete(user_id=...)` pre všetky jeho krátkodobé kontexty, dlhodobé spomienky,
projektové fakty, ktoré vlastní, a používateľsky viazané auditné udalosti. Konkrétny
záznam možno odstrániť pridaním `record_id`. Projektový export alebo výmaz používa
`project_id` a vyžaduje samostatné autorizačné overenie. Počet odstránených riadkov
treba zaznamenať do externého bezpečnostného auditu bez pôvodného obsahu a pri
produkčnej databáze treba uplatniť rovnakú lehotu aj na zálohy.
