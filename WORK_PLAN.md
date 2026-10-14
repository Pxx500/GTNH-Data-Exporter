# Plan pracy: przygotowanie danych i lepsze wyszukiwanie receptur

**Data:** 2026-10-14  
**Status:** pierwotny zakres implementacji ukończony. Wyniki zapisano w WORK_RESULTS.md.
Dalsze zatwierdzone badania i poprawki są śledzone poniżej oraz w SEARCH_EXPERIMENTS.md.

## Cel

Przygotować dataset GTNH przed zapytaniami tak, żeby wyszukiwanie znajdowało
bardziej użyteczne dla developera trasy, obejmowało istotne gałęzie produktu
docelowego i zużywało mniej pracy na eksplorację mało istotnych powiązań.

Precomputation jest kierunkiem pracy. Wyspy receptur są hipotezą badawczą,
a nie narzuconym algorytmem. Wybieramy rozwiązanie na podstawie literatury,
własności naszego modelu receptur i porównań na rzeczywistych danych.

## Zasady pracy po sygnale startu

- Użytkownik zatwierdził start oraz samodzielne rozstrzyganie decyzji o małym ryzyku.
- Praca trwa do ukończenia uzgodnionego zakresu albo do sygnału powrotu lub
  przerwania od użytkownika. Poranek sam w sobie nie kończy pracy.
- Główny agent koordynuje, szuka problemów, rozstrzyga decyzje i integruje wyniki.
- Maksymalnie pięciu aktywnych subagentów. Bezczynny pomocnik nie rezerwuje slotu.
  Pomocnik Luna max wykonuje proste, ograniczone zadania zbierania danych.
  Złożone badania, projektowanie, programowanie i przegląd zostają z Sol 6.1 high
  lub głównym agentem. Nie uruchamiamy agentów tylko po to, żeby wypełnić limit.
- Zadania równoległe mają rozłączne odpowiedzialności za pliki i procesy.
- Badanie metod, audyt pokrycia, zbieranie benchmarków i domknięcie GUI mogą
  iść równolegle. Zmiany przygotowania indeksu i wyszukiwania mają wspólnego
  właściciela, żeby agenci nie przebudowywali niezależnie tego samego silnika.
- Poprawiamy potwierdzone problemy. Nie zamieniamy zadania w bezterminowy audyt.
- Zmiany zapisujemy w lokalnych, tematycznych commitach. Publikacja pozostaje
  osobną decyzją użytkownika.

## Co wiemy na początku

- Bieżący snapshot: `2830da9f-c040-4233-a778-036e4b27f3eb`.
- Zawiera 118 717 zasobów, 186 528 grup i 259 781 procesów.
- EBF występuje jako rodzina `gregtech:gt.recipe.blastfurnace`: 2033 procesy.
  Pięć produkuje kanoniczny Steel Ingot. Przykładowa receptura z Iron Dust ma
  120 EU/t, 500 ticków i wymaganie ciepła 1000. Jej klasa napięcia to MV.
- Występuje też `gregtech:gt.recipe.primitiveblastfurnace`: 418 procesów,
  w tym 46 produkujących ten Steel Ingot. Obecność nie dowodzi pełności eksportu.
- `Dataset.import_snapshot` już tworzy indeks SQLite z tabelami inputów,
  outputów, członkostwa grup i tożsamości zasobów. Rozwijamy istniejącego właściciela.
- `Dataset._find_paths` już ma wyszukiwanie najkrótszej trasy, ograniczoną
  eksplorację od źródła, odkrywanie wstecz od składników celu i cache w obrębie
  zapytania. Nie zakładamy, że wyszukiwanie jest wyłącznie ślepym forward BFS.
  Tryb diverse ma m.in. limit 10 000 odczytanych procesów, 40 000 stanów i
  100 000 jednostek pracy rozwijania powiązań. Trzeba zmierzyć, co wyczerpuje te budżety.
- Zgłoszony problem: trasa przez wodór jako produkt uboczny może wypierać
  oczekiwaną drogę przez stal. Trzeba odtworzyć go dla dokładnego itemu docelowego.
  LV Machine Casing, LV Machine Hull i gotowa maszyna mają różne wymagania.

## Lista prac

### 1. Baseline i przykłady definiujące oczekiwane zachowanie

- [x] Rozpoznać dokładne tożsamości materiałów i produktów w bieżącym snapshotcie.
- [x] Przygotować przypadki Iron Dust → LV Machine Casing, Iron Dust → LV Machine
  Hull, Crushed Iron Ore → Double Iron Plate i Iron Dust → Volcanus Controller.
- [x] Dla każdego zapisać dostępne w dumpie sensowne drogi, wymagane składniki
  poboczne oraz wyniki obecnego wyszukiwania. Nie wymyślać brakujących receptur.
- [x] Powtórzyć odpowiednie przykłady z jawnymi limitami LV i MV oraz bez limitu.
- [x] Dodać regresje dla OR, NBT, wymaganej obecności narzędzia, wariantów
  kanonicznych i niekanonicznych oraz tras przechodzących przez cykle.
- [x] Zachować wodę → wodór i znany obieg regeneracyjny jako regresję audytu
  energii. Nowe preferencje ścieżek materiałowych nie mogą ukryć takich obiegów.
- [x] Zmierzyć czas, unikalne odczytane procesy, rozwinięcia dopasowań i stanów,
  powtarzaną pracę, osiągane limity oraz pokrycie gałęzi celu.
- [x] Porównać pierwsze zapytanie po uruchomieniu klienta z kolejnymi zapytaniami.
  Nie ukrywać kosztu przygotowania indeksu albo rozgrzewania cache.

**Wynik:** powtarzalny zestaw porównań z oczekiwaniami opartymi na danych.

### 2. Porównanie istniejących metod i wybór kierunku

- [x] Przejrzeć pierwotne źródła dotyczące wyszukiwania kierowanego celem,
  A* i dolnych oszacowań, przygotowania informacji o osiągalności, hierarchicznej
  abstrakcji grafu oraz planowania w grafach AND/OR lub sieciach reakcji.
- [x] Wybrać do testu dwa lub trzy uzasadnione podejścia. Punktem odniesienia jest
  obecny algorytm z istniejącymi indeksami, nie sztucznie osłabiony baseline.
- [x] Sprawdzić, ile daje lepsze wykorzystanie obecnych indeksów i współdzielenie
  przygotowanych dopasowań między zapytaniami, zanim dodamy kolejną strukturę.
- [x] Osobno ocenić szybkość, dobór użytecznych tras i pokrycie alternatyw.
  Szybszy algorytm, który gubi drogę przez stal, nie spełnia celu.
- [x] Zapisać wybraną metodę, źródła, odrzucone alternatywy i wyniki pomiarów.

**Wynik:** uzasadniona decyzja, a nie implementacja pierwszego pomysłu.

### 3. Eksperyment z wyspami i połączeniami na wyższym poziomie

- [x] Porównać grupowanie według cykli, materiałów lub rodzin przemian z innymi
  metodami abstrakcji, jeśli badania wskazują, że warto je sprawdzić.
- [x] Zmierzyć rozmiary grup, udział największej grupy, liczbę przejść między
  grupami i wpływ hubów takich jak woda, wodór oraz tlen.
- [x] Zachować konkretne receptury i zasoby w eksperymentalnym grafie.
  Sama sekwencja wyspa 1 → 2 → 4 nie dowodzi poprawnego chaina.
- [x] Ocenić wymagania dla poprawnego przejścia przez wyspę i świadków AND/OR.
  Nie wdrożono makrotras, więc nie przedstawiamy relaksowanej osiągalności jako
  dowodu spełnienia wszystkich składników.
- [x] Ocenić zasadność makro → mikro na pomiarach grup i portali oraz porównać
  pozostałe kandydaty z baseline. Negatywny wynik SCC zakończył tę gałąź badań
  przed implementacją pełnego wyszukiwania makro → mikro.
- [x] Przyjąć wyspy do produkcyjnego wyszukiwania tylko przy wykazanej korzyści.
  Negatywny wynik eksperymentu jest poprawnym wynikiem badania.

**Wynik:** decyzja, czy ta abstrakcja pomaga naszemu datasetowi.

### 3a. Eksperyment z odległością od źródeł w grze

- [x] Sprawdzić hipotezę użytkownika: potwierdzone źródła itemów ze świata gry
  otrzymują poziom 0, a kolejne przemiany zwiększają odległość od pozyskania.
  Jest to wyliczona wskazówka do wyszukiwania, a nie entropia fizyczna.
- [x] Porównać poziom receptury oparty na najdalszym wymaganym składniku z kosztem
  sumującym drogi składników. Uwzględnić wszystkie sloty AND i legalne wybory OR.
  Osobno traktować narzędzia wymagane przez obecność oraz ich pozyskanie.
- [x] Zachować nieznaną odległość przy braku dowodów. Generowany blok, potencjalny
  drop z reguły i potwierdzony item wydobycia nie są tym samym źródłem poziomu 0.
  Jawne podstawowe surowce profilu mogą tworzyć oddzielny zestaw założonych wejść.
- [x] Nie pozwolić cyklom bez wejść ze źródeł uzyskiwać sztucznie niskiego poziomu.
  Sama malejąca liczba nie dowodzi wykonalności, dobrego uzysku ani braku strat.
- [x] Zmierzyć przydatność tej wskazówki do porządku eksploracji i propozycji granic
  Target from basics. Sprawdzić skróty przez wodę, wodór i produkty uboczne.
  Wdrożyć ją tylko przy potwierdzonej korzyści i z jawnym opisem ograniczeń.

**Wynik:** sprawdzona hipoteza potencjału źródłowego z porównaniem metod oraz
decyzją o użyciu lub odrzuceniu jej w produkcyjnym wyszukiwaniu.

### 4. Przygotowany indeks przepływów

- [x] Wdrożyć wybrane przygotowanie po dumpie, poza głównym wątkiem gry.
- [x] Oprzeć je na istniejącym imporcie i właścicielu `Dataset`. Szczegóły
  przechowywania ustalić po pomiarach, zaczynając od obecnego SQLite.
- [x] Przygotować potrzebne powiązania, dopasowania, cechy materiałowe,
  informacje o cyklach, osiągalności lub przejściach między grupami.
  Zakres wynika z wybranej metody, nie z chęci zapisywania wszystkiego.
- [x] Kontrolować koszt grup i alternatyw. Nie materializować wszystkich kombinacji
  składników ani wszystkich możliwych chainów, jeśli wystarczy zapis symboliczny.
- [x] Zachować pełne receptury, ilości, szanse, AND/OR, NBT i warunki. Nie scalać
  tożsamości przedmiotów tylko dlatego, że mają podobną nazwę lub wspólną grupę.
- [x] Oddzielić dane źródłowe od wyliczonych wskazówek. Niepewne informacje
  pozostają niepewne, a hipotezy nie stają się warunkami wykonania receptury.
- [x] Powiązać indeks ze snapshotem i wersją analizy. Umożliwić jawne
  przebudowanie bez ponownego uruchamiania Minecrafta i bez cichego mieszania wersji.
- [x] Zmierzyć czas przygotowania, rozmiar, pamięć, start klienta i wpływ na zapytania.

**Wynik:** przebudowywalny indeks używany przez wspólny silnik zapytań.

### 5. Użyteczne trasy i uczciwy opis ich zakresu

- [x] Używać przygotowanych danych również do wyboru kolejności eksploracji.
  Sam ranking wyników po osiągnięciu limitu nie wystarczy.
- [x] Preferować istotny przepływ materiału od A do części konstrukcyjnych B,
  jeśli potwierdzają go dane. Nie kodować wyjątków dla żelaza lub stali.
- [x] Oczekiwana droga przez stal ma pojawiać się bez ręcznego wpisywania stali
  jako wymaganego materiału przejściowego. Takie wymuszenie nie naprawia heurystyki.
- [x] Zachować trasy przez produkty uboczne i opisać ich rolę. Nie oznaczać ich
  jako błędnych tylko dlatego, że są mniej intuicyjne.
- [x] Pokazywać, które gałęzie produktu wyjaśnia wynik, jakie inne składniki są
  potrzebne oraz gdzie wyszukiwanie lub wiedza się kończy.
- [x] Zachować znaczenie istniejących trybów i filtrów. Jeśli preferencja
  materiałowa wymaga osobnego trybu, nazwać go jawnie zamiast zmieniać po cichu
  definicję najkrótszej ścieżki.
- [x] Udostępnić tę samą logikę przez GUI, HTTP, CLI i MCP. Zaktualizować opisy
  oraz przewodnik dla agentów, łącznie z przyczynami wyboru i ograniczeniami wyniku.

**Wynik:** droga przez stal jest odnajdywana i odpowiednio prezentowana,
a powiązanie przez wodór nie udaje wyjaśnienia stalowej części urządzenia.

### 6. Pokrycie maszyn i warunków

- [x] Porównać odpowiednie rodziny i receptury z rejestrami działającej gry oraz
  NEI. Oddzielić brak eksportu od błędu dopasowania, filtra, etykiety i wyszukiwania.
- [x] Zweryfikować EBF oraz podstawowe maszyny na ścieżkach z zestawu przykładów,
  w tym ilości, alternatywy składników, napięcie i wymagania ciepła.
- [x] Poprawić potwierdzone luki potrzebne do tych przypadków i pokazać porównanie
  przed i po. Sama obecność rodziny albo zgodność liczby rekordów nie wystarcza.
- [x] Jeśli potrzebny jest nowy dump, kontrolować wersje paczki i konfigurację.
  Wyników z różnych wersji GTNH nie traktować jako porównania samego algorytmu.

**Wynik:** potwierdzone pokrycie istotnych rodzin albo konkretna lista luk z dowodami.

### 7. Czytelne informacje o dostępności materiałów

- [x] Usunąć rutynowy badge „Captured producer” z podpowiedzi wyszukiwania.
  Obecnie oznacza co najmniej jedną zapisaną, interpretowalną recepturę z tym
  materiałem na wyjściu. Nie sprawdza, czy da się zdobyć wszystkie jej składniki
  i spełnić warunki, więc nie jest dowodem dostępności materiału w grze.
- [x] W szczegółach zachować tę informację pod zrozumiałą nazwą, np. „Receptury
  produkcji w dumpie”, wraz z liczbą i przykładami receptur oraz ich warunkami.
- [x] W autocomplete wyróżniać informacje, które wpływają na wybór materiału,
  np. wariant zastępowany przez unifikację, niejasne receptury lub brak znanej
  drogi pozyskania. Rutynowe pozytywne informacje nie powinny zajmować osobnego
  wiersza przy każdym wyniku.
- [x] Rozróżniać obecność receptury, znane źródło i pełną drogę pozyskania.
  Braku dowodów w niepełnym dumpie nie przedstawiać jako pewnej niemożliwości
  zdobycia itemu. Wyjaśnić ostrzeżenia i umożliwić sprawdzenie ich podstawy.
- [x] Sprawdzić podpowiedzi na GT Iron Dust i wariancie IC2. Ujednolicić znaczenie
  statusów w GUI i dokumentacji MCP, zachowując dane o dowodach dla agentów.

**Wynik:** lista wyników jest czytelniejsza, a oznaczenia pomagają wybrać właściwy
materiał i nie sugerują dostępności, której analiza nie potwierdziła.

### 8. Surowce pierwotne i pochodzenie ze świata gry

- [x] Rozdzielić fakt „ma źródło w świecie gry” od roli „surowiec podstawowy
  w tym planie”. Obecne profile podstawowych surowców są deklaracją granicy
  planowania, a nie potwierdzeniem pochodzenia albo dostępności w grze.
- [x] Oznaczać bezpośrednie źródła na podstawie eksportowanych definicji,
  np. generacji złóż, dropów lub pozyskania płynów. Pokazywać rodzaj źródła,
  wymiary i warunki oraz dowody. Receptura recyklingu nie odbiera tego oznaczenia.
- [x] Oddzielić generowany blok rudy od itemu otrzymywanego podczas wydobycia.
  Sama obecność bloku w oregenie nie dowodzi, że gracz dostaje ten blok albo
  konkretny crushed ore. Zachować rozróżnienie potwierdzonego dropu i kandydata
  wywnioskowanego z reguły wydobycia.
- [x] Zbadać osobne oznaczenie „produkt wstępnego przetwarzania surowca”,
  np. crushed ore. Wnioskować z rodzaju procesu i udokumentowanego pochodzenia,
  z ograniczonym zakresem kroków. Nie rozszerzać tagu automatycznie na każdy
  osiągalny produkt. Wyniki heurystyczne muszą mieć wyjaśnienie i poziom pewności.
- [x] Nie definiować pierwotności jako braku receptur ani braku cykli.
  Odnawialność traktować osobno. Istnienie cyklu nie dowodzi odnawialności,
  bo obieg może wymagać zużywanych składników i zapasu rozruchowego.
- [x] Korzystać z tych oznaczeń w wyszukiwaniu i jako podpowiedzi przy tworzeniu
  profilu Target from basics. Użytkownik zatwierdza granicę planowania.
  Nie przerywać automatycznie rozwijania receptur na każdym oznaczonym materiale.
- [x] Sprawdzić iron ore, jego rzeczywisty produkt wydobycia, crushed ore,
  Iron Dust i niekanoniczny wariant IC2. Obecność w rejestrze lub recepturach
  nie zastępuje dowodów aktywnego źródła w danej konfiguracji paczki.

**Wynik:** oznaczenia wyjaśniają pochodzenie materiału, nawet gdy istnieją też
drogi recyklingu. Granica planera pozostaje jawnym wyborem użytkownika.

### 9. Inspekcja bez utraty planszy i czytelne szczegóły

- [x] Naprawić utratę stanu Trace przy przejściu do Library i powrocie.
  Zachować wynik, filtry, pozycje kafelków, kamerę i wyróżnioną ścieżkę.
  Inspekcja nie powinna uruchamiać nowego wyszukiwania ani resetować planszy.
- [x] Kliknięcie materiału lub receptury ma otwierać szczegóły przy planszy.
  Dociągać rekord brakujący w lokalnym wyniku zamiast przenosić użytkownika
  do Library. W obecnym kodzie lokalny materiał otwiera panel, ale brak lokalnego
  rekordu i przycisk „Inspect in library” wywołują zmianę widoku.
- [x] Oddzielić „Pokaż szczegóły”, „Otwórz w Library” i „Użyj w nowym zapytaniu”.
  Nazwa przycisku ma opisywać skutek. Jawne przejście do Library ma zapewniać
  powrót do zachowanej planszy. Nie rozszerzać tego zadania na zapis sesji po restarcie.
- [x] Umieścić nagłówek i zamknięcie panelu poza przewijaną treścią, tak żeby
  „Close” pozostawał widoczny przy długich rekordach i w wąskim widoku.
  Zapewnić obsługę klawiaturą i powrót fokusu po zamknięciu.
- [x] Domyślnie pokazywać nazwę, ilość, jednostkę, niepewną szansę w procentach
  i istotne warunki. Ukryć rutynowe 100%, surowe numerator/denominator oraz
  wewnętrzne identyfikatory slotów. Nie usuwać informacji potrzebnych do
  zrozumienia zużycia, narzędzi, alternatyw i warunków wykonania.
- [x] Przenieść fragmenty „Output fields” i podobne JSON-y z pojedynczych
  składników do wyraźnego widoku danych technicznych, domyślnie ukrytego.
  Zachować pełny rekord i możliwość jego skopiowania dla developera.
- [x] Przejść najważniejszy przepływ: wyszukanie → graf → szczegóły składnika
  → receptury produkcji → powrót do grafu → zamknięcie panelu. Poprawić konkretne
  niejasne etykiety, skutki akcji i powody blokady przycisków w tym przepływie.
  Nie zamieniać tego zadania w pełne przeprojektowanie wszystkich ekranów.
- [x] Sprawdzić utrzymanie stanu po inspekcji i zmianie zakładki, brak skoków
  nawigacji, widoczność zamknięcia podczas scrolla i zgodność danych technicznych
  z czytelnymi ilościami oraz procentami.

**Wynik:** można badać receptury i materiały bez utraty wyników oraz ustawienia
planszy. Domyślny widok zawiera informacje potrzebne do pracy, a techniczne
szczegóły są dostępne na żądanie.

### 10. Domknięcie rozpoczętego GUI i końcowa weryfikacja

- [x] Dokończyć bieżące zmiany scrolla i eksportu planszy w osobnym commicie.
  Końcowy kod przechodzi 63 testy GUI. Wcześniejszy PNG miał 4514 × 3992 px.
  Końcowy PNG ma 3976 × 7902 px, a SVG zawiera 16 kafelków, 17 połączeń
  i 17 podpisów. Pełny Python ma 162 testy, a eksporter 30.
- [x] Potwierdzić końcowy scroll nad tłem i kafelkami. Zoom Ctrl+scroll ma
  regresję GUI. Natywnie sprawdzono kontrolki zoomu, a CUA nie dostarczyło
  osobnego dowodu dla przytrzymanego Ctrl podczas wheel.
- [x] Sprawdzić zapis przez widoczny link pobierania. CUA nie potwierdził
  zdarzenia pobrania, choć renderer i linki zwróciły poprawne pliki. Wynik tej
  próby pozostaje niejednoznaczny. Fizyczny zapis w przeglądarce nie jest
  zweryfikowany, a wygenerowane pliki zachowano lokalnie.
- [x] Zweryfikować aktualny silnik na przykładach natywnych i odpowiednich
  testach po zmianach. Sprawdzić zgodność wyników między interfejsami.
- [x] Przygotować jeden zbiorczy przegląd, poprawić potwierdzone problemy
  w zakresie i wykonać skupiony przegląd poprawek.
- [x] Zakończyć raportem: wyniki pomiarów, poprawione zachowania, decyzja o wyspach,
  potwierdzone luki i ograniczenia. Nie ogłaszać pełnego pokrycia całej gry.

## Warunek ukończenia

- Oczekiwane, istniejące w dumpie drogi z zestawu przykładów są znajdowane przy
  pasujących filtrach, a gałęzie i dodatkowe wymagania są opisane zgodnie z danymi.
- Wybrana metoda przygotowania i wyszukiwania ma porównanie przed i po pod
  względem pracy, czasu, pamięci i jakości tras. Istotne regresje są wyjaśnione.
- Wyspy zostały przyjęte na podstawie wyników albo odrzucone z udokumentowanym
  powodem. Nie są obowiązkowym rezultatem implementacji.
- Potwierdzone problemy potrzebne do uzgodnionych przykładów są poprawione.
  Niewykonane wymagania nie stają się ukończone przez samo opisanie ich w raporcie.
  Dalsze potrzeby odkryte poza zakresem zapisujemy do późniejszej decyzji użytkownika.
- Inspekcja i powrót z Library zachowują planszę. Zamknięcie panelu pozostaje
  dostępne podczas przewijania, a JSON nie zaśmieca domyślnego widoku składników.
- Oznaczenia źródeł materiałów odróżniają dowody, heurystyki i granice profilu.
  Recykling nie usuwa oznaczenia źródła w świecie gry.
- Kod, dokumentacja i dowody są zapisane, a pozostałe ograniczenia są jawne.

## Otwarte punkty do wspólnego dopracowania

- Czy przykład z kablami dotyczy LV Machine Hull, czy konkretnej gotowej maszyny?
  Zestaw testów obejmuje casing i hull, ale warto dopisać dokładny zgłoszony cel.
  Brak tego doprecyzowania nie blokuje pozostałych przykładów ani badań.
- Jaką poprawę na benchmarkach uznamy za wystarczającą? Progi ustalimy po
  zebraniu baseline. Nie wpisujemy z góry obietnicy typu 100× szybciej.
- Czy poza tym zakresem są jeszcze wymagania, które użytkownik chce dopisać?

## Decyzje i postęp po starcie

- Rozdzielono pięć odpowiedzialności: silnik i benchmarki, badanie algorytmów,
  pokrycie maszyn, pochodzenie materiałów i przepływ GUI. Główny agent integruje
  transporty, dokumentację i końcową weryfikację.
- Przygotowane dane przepływu pozostają pochodną kanonicznego dumpa. Rozważono
  dodatkowe tabele w istniejącym indeksie i osobny przebudowywalny sidecar.
  Wybrano sidecar zarządzany przez Dataset, żeby zachować bazowy indeks bez zmian
  i umożliwić niezależne wersjonowanie oraz atomowe odtworzenie analizy.
- Nowa preferencja materiałowa otrzymuje jawny tryb `path_selection=material`.
  Istniejące `shortest` i `diverse` zachowują swoje znaczenie. Pomiary zdecydują
  o domyślnej opcji GUI. Receptury i ich warunki pozostają źródłem prawdy.
- Pierwszy eksperyment wysp SCC daje jedną bardzo dużą grupę. Usunięcie wody,
  wodoru i tlenu praktycznie jej nie rozbija. Trwa porównanie z przygotowaniem
  symbolicznych dopasowań, a szczegóły zostaną zapisane w raporcie badania.
- Bazowy scroll sprawdzony w rzeczywistej przeglądarce po wcześniejszej poprawce:
  nad tłem i kafelkiem zmienia się pozycja strony, a kamera grafu pozostaje stała.
  Dowody: `exports/graph-ux-proof-20261014/wheel-proof.json`.

## Zamknięcie zakresu

- Nowy snapshot: `779ea030-ae9c-40ea-8854-99a176f7cc42`. Bazowy dump pozostaje
  niezmieniony. Oba porównania z NEI mają 78 389 dopasowań i zero różnic
  w obsługiwanym zakresie, z zachowanymi 15 błędami przechwytywania.
- Wyspy SCC oraz sam potencjał odległości od źródeł nie weszły do produkcyjnej
  heurystyki. Wynik eksperymentów i odrzucone kierunki są zapisane, bez
  przypisywania im dowodu wykonalności AND.
- Przygotowany indeks, tryb materiałowy, oznaczenia pochodzenia oraz poprawki
  GUI działają. MCP ma jawny compact/full i kompletny przewodnik 25 narzędzi.
- Bieżące połączenie MCP tej rozmowy nadal wskazuje stary snapshot. Zapisana
  konfiguracja i nowy klient SDK wskazują nowy. Nie utożsamiamy tych stanów.
- Potencjał źródłowy, nierozwiązane zachowanie narzędzi craftingu, niepełne
  rodziny i konfiguracje oraz niepotwierdzone natywne pobieranie przez CUA
  pozostają ograniczeniami opisanymi w WORK_RESULTS.md.
- Otwarte pytanie o dokładną gotową maszynę użytkownika pozostaje opcjonalnym
  rozszerzeniem benchmarków. Casing, hull, double plate i Volcanus sprawdzono.
- Końcowy Volcanus na świeżym snapshotcie zwrócił sześć ścieżek w 0,437 s,
  w tym stal → tungstensteel → Robot Arm IV. Reprezentuje 8/15 gałęzi,
  z limitem 20 000 kolejkowanych stanów. Ta granica pozostaje jawna.

## Dalsze badania po zamknięciu pierwszego zakresu

Użytkownik zlecił dalsze badania i poprawki. Wyniki powyżej opisują poprzedni
etap. Bieżące pomiary i decyzje są w SEARCH_EXPERIMENTS.md.

- [x] Wprowadzić częściowe rozwijanie następców bez usuwania konkretnych
  receptur. Volcanus zwraca osiem ścieżek i obejmuje 10/15 gałęzi przy
  wcześniejszych limitach. Zaoszczędzone przyjęcia do kolejki nie oznaczają
  usunięcia kosztu skanowania kandydatów.
- [x] Usunąć identyczne kontynuacje tego samego kroku powstałe przez
  powtarzające się sloty. Wszystkie wyniki ośmiu przypadków pozostają takie
  same. Volcanus z ograniczeniem LV rozpatruje 2673 zamiast 3113 stanów.
  Pełna receptura nadal zawiera wszystkie sloty. Regresja dużej liczby
  powtórzeń przechodzi, bez zwiększania limitu kolejki.
- [x] Sprawdzić preferencję przetwarzania materiału przed konstruowaniem
  komponentu wyłącznie po to, żeby go rozebrać. Miękka preferencja usuwa
  zaobserwowane objazdy przez budowę narzędzi. Wymagany recykling pozostaje
  legalny. Wszystkie 167 testów Pythona przechodzi.
- [x] Sprawdzić aliasy materiał/formy, dodatkowe składniki przy ustawianiu
  gałęzi i konkretne przejścia wewnątrz regionów. Same aliasy i kolejność
  gałęzi nie poprawiają wyników. Regiony zachowują świadków, ale mają dużo
  wyjść i wymagają sprawdzania historii. Nie promować tych prób do produkcji.
- [x] Pozyskać bezpośrednie deklaracje materiałów i form GT++ oraz sprawdzić
  je w prawdziwej paczce. Nowy odrębny dump ma 1709 deklaracji właściciela.
  Nie utożsamiać tych deklaracji z bilansem chemicznym ani globalną
  tożsamością materiału.
- [x] Sprawdzić typy przejść jako mapę znaczeń: zmiana formy, przetwarzanie
  rudy, zmiana materiału, montaż, odzysk i nieznane. Porównać na tych samych
  ośmiu przypadkach i limitach. Rozróżnić potrzebny krok od powrotnego
  objazdu. Sprawdzić zachowanie gałęzi przez stal, konstrukcję komponentów,
  produkty uboczne i wymagany recykling.
  Kara za samą zmianę formy daje regresję i nie trafia do produkcji. W badanych
  trasach nie zaobserwowano powrotu do tej samej sygnatury formy, a kara usuwa
  potrzebne kroki. Spis typów przejść pozostaje dowodem do dalszych badań.
- [x] Sprawdzić natywne role wejść, zwłaszcza narzędzie do craftingu i materiał
  produkcyjny. Oprzeć je na grupach i deklaracjach receptury, bez zgadywania
  po nazwach. Nie zmieniać zużywanego narzędzia w nieznikającą obecność ani
  nie wywodzić pochodzenia atomów z samego udziału składnika.
  Kara w wyszukiwaniu nie poprawia wyników i jest kosztowna. Dodano zamiast
  niej adnotacje wybranych wejść oraz krótkie wyjaśnienie w GUI. Natywne
  ścieżki i liczniki wyszukiwania pozostają takie same. Adnotacja kosztuje
  około 3 ms, a 173 testy Pythona i 64 testy GUI przechodzą.
- [x] Uzupełnić natywne deklaracje GT++ o właścicieli płynów. Korzystać z
  rzeczywistych referencji w istniejącym rejestrze, bez fabryk i zgadywania
  nazw. Zachować wszystkich kandydatów, oddzielić te dane od bilansów i
  potwierdzić odczyt w jednym odrębnym eksporcie.
  Potwierdzono 268 właścicieli płynów i zgodne deklaracje stopionych
  Hastelloy-W/N z ich komponentami. Paczka przeszła na `.225`, więc
  nowy dump zachowuje nieobsługiwane bilanse zamiast przyjmować tę wersję
  bez dowodów zgodności. Aktywny snapshot pozostaje bez zmian.
- [x] Sprawdzić literaturę o grupach podobnych zastosowań i ścieżkach po
  typach relacji. Odróżnić je od grup SCC i przygotować najwyżej jeden mały
  test sygnatur zastosowań na obecnych danych. Nie traktować podobieństwa
  jako dowodu osiągalności ani nie dodawać dużego treningu bez wyników.
  Profile rodzin produkujących i zużywających rozpoznają postacie materiałów
  lepiej niż kontrola stopnia grafu: 75,76% wobec 30,30% w 33 przypadkach.
  To wynik pośredni. Nie potwierdza jakości tras ani zastosowań 17 komponentów
  bez niezależnych etykiet. Koszty przygotowania i odczytów pozostają jawne.
- [x] Sprawdzić jeden wariant kierowania wyszukiwaniem na podstawie profili
  zastosowań składników celu. Porównać te same osiem przypadków i limity,
  zachować wszystkie natywne kroki i policzyć przygotowanie. Nie promować
  samego podobieństwa form, jeśli nie poprawia jakości konkretnych tras.
  Wszystkie osiem przypadków zachowuje te same ścieżki. Mediana czasu rośnie
  o 82%, a pamięć o 58–69 MiB. Odrzucono badane sortowanie remisów bez tuningu.
- [x] Oddzielić brak gałęzi wynikający z limitu zwracanych tras od budżetu
  skanowania. Volcanus przy 16 wynikach zwraca 12 tras i pokrywa 15/15 gałęzi,
  zachowując limity skanowania. Rzeczywista praca rośnie, co raportujemy osobno.
- [x] Sprawdzić dolne oszacowanie pozostałego kosztu dla wewnętrznej kolejki.
  Użyć tylko rozdzielnych, istniejących kosztów, zachować rzeczywisty koszt
  przy porównywaniu stanów i końcowe sortowanie. Dowód dotyczy kosztu kolejki,
  który różni się od końcowej oceny trasy. Policzyć pełne przygotowanie i
  porównać osiem przypadków przy dotychczasowych limitach.
  Oszacowanie jest poprawne dla kolejki i zmniejsza pracę, ale traci jedną
  gałąź Computer Cube przy tym samym limicie wyników. Całość ośmiu zapytań
  z przygotowaniem jest wolniejsza. Nie promujemy tego wariantu do produkcji.
- [x] Sprawdzić profil kosztów bieżącego zapytania i usunąć zbędną pracę.
  Odczyt informacji materiałowych na żądanie zastępuje dekodowanie niemal
  119 tysięcy rekordów odczytem 239–2096. Osiem przypadków zachowuje wszystkie
  wyniki i liczniki. Mediany czasu spadają o około 6–25%, a 173 testy przechodzą.
- [x] Sprawdzić możliwość ścisłego bilansu GT++ na podstawie nowych deklaracji.
  Brakuje niezależnej podstawy ilości i tożsamości pierwiastków. Nominalne
  ilości form pozostają informacją o przetwarzaniu, bez certyfikacji chemii.
- [x] Zachować natywne odwołania do katalogów GT i GT++ oraz szablonów maszyn.
  Dopasować surowe wpisy po pełnej tożsamości bez normalizacji i nowych itemów.
  Sprawdzić layout prywatnego pola GT++ i jawnie raportować błąd kolektora.
  Potwierdzić sześć badanych komponentów w jednym odrębnym eksporcie.
  Wszystkie sześć przykładów ma poprawne odwołania. Zgodnych jest 118719
  tożsamości i wszystkie wcześniejsze pola surowców. Nie powstały nowe itemy
  wyłącznie z katalogu. Przechodzą 32 testy Javy, a chronione bazy mają te same
  hashe. Te dane nie nadają jeszcze automatycznie ról semantycznych.
- [x] Sprawdzić dokładny profil ilości `.225` i po dowodach zgodności wykonać
  jeden osobny eksport z nowymi odwołaniami oraz obsługiwanymi bilansami.
  Zachować starsze wersje i nierozwiązane dumpy bez zmian. Nie przełączać
  aktywnej bazy ani nie rozszerzać obsługi na niezweryfikowane wersje.
  Wszystkie 15 plików źródłowych i 22 klasy są identyczne. Świeży dump ma
  4695 zgodnych wektorów wobec obu wcześniejszych wspieranych wersji oraz
  zachowuje 6541 odwołań źródłowych. Przechodzi 173 testów Pythona i 32 Javy.
- [x] Dodać wykluczanie przechwyconych grup wariantów w Trace, GUI i MCP.
  Rozwiązać dosłownych członków raz w Dataset, zachować pełne receptury i
  ograniczenia ścieżki. Nie utożsamiać grup ore i unified ani grupy nuggetIron
  z formą wszystkich nuggetów. Nie publikować nowego GUI do starego backendu.
  Testy obejmują trzy polityki, aliasy i literalne NBT oraz transporty. W
  przeglądarce grupa nuggetIron usuwa nuggety ze ścieżek, zachowując cztery
  trasy. Kompaktowy widok zmniejsza zasób danych z 1724 do 21 surowców,
  zachowując dziesięć pełnych receptur. Osobna instancja została zamknięta.
- [x] Sprawdzić wybór ośmiu tras z tej samej zapisanej puli dwunastu.
  Pokrycie rośnie z 10 do 11 gałęzi, ale selektor traci historię casingu i
  dodaje udział młotka w produkcji płyty. Nie promujemy samej metryki pokrycia.
  Koszt zebrania większej puli pozostaje osobny od taniego wyboru wyników.
- [x] Sprawdzić przyszłą możliwość zachowania natywnego pochodzenia GT++
  na granicy fabryki, zanim utracona zostanie referencja do GT enumu.
  Odróżnić pochodzenie od tożsamości chemicznej, jednostek form i czystości.
  Na razie badanie źródeł bez instrumentacji ani uruchamiania gry.
  Fabryka pozwala obserwować faktyczne pochodzenie nowego obiektu, ale nie
  kopiuje komponentów ani normalizacji ilości. Bezpośrednie konstrukcje W/N
  pozostają poza tym miejscem. Brakuje konfiguracji i zależności kompilacji
  hooka oraz dowodu instalacji przed inicjalizacją. Instrumentację odkładamy.
- [x] Sprawdzić, czy dominacja stanów według materiału i formy może ograniczyć
  zbędne obiegi bez utraty wymaganych składników, historii i pełnych receptur.
  Nie powtarzać odrzuconej kary za formy ani usuwać loopów z audytu balansu.
  Natywny kontrprzykład wymaga przejścia Steel Ingot do Steel Dust przed
  mikserem. Materiał obu form jest identyczny, ale tylko dust pasuje do wejścia.
  Dominacja według samego materiału ucina ten potrzebny most. Odrzucono ją.
- [x] Sprawdzić opisowe rozróżnienie przemiany materiału od udziału narzędzia
  i zależności pobocznej. Użyć istniejących deklaracji, zachować niepewność
  i nie nazywać podobieństwa składu dowodem pochodzenia atomów.
  Obecne pola pozwalają opisać postać, materiał, rodzinę procesu i kategorię
  wejścia. Nie przypisują materiału z konkretnego wejścia do konkretnego wyjścia.
  Potwierdzono lukę kategorii narzędzi z NBT i natywne API do jej uzupełnienia.
- [x] Zachować rzeczywiste dopasowanie kategorii OreDictionary dla itemów,
  również wariantów narzędzi z NBT. Użyć sprawdzonego natywnego getOreIDs,
  oddzielić te dane od dosłownych członków grup i ograniczeń wyszukiwania.
  Potwierdzić jeden odrębny dump, adnotacje, starsze obsługiwane snapshoty
  oraz opis podstawy rozpoznania w GUI i MCP. Nie zmieniać oceny tras.
  Jeden dump potwierdza 117299 poprawnych odczytów bez błędów, w tym wariant
  młotka z NBT. Wszystkie wcześniejsze pola surowców i zestawy członków grup
  są zgodne. Przechodzi 180 testów Pythona, 67 GUI i 32 Javy. HTTP, nowy
  klient MCP i osobne GUI potwierdzają adnotację. Główna instancja bez zmian.
  Nie stwierdzamy pełnej zgodności kolejności i warunków wszystkich procesów.
- [x] Zweryfikować rzeczywiste ilości i wymagania Eye of Harmony. Zbadać,
  czy ogólny zapis GT jest oznaczonym proxy, czy trafia do planera jako zwykła
  receptura. Zachować natywne ilości long i zależności wykonania bez zgadywania
  ustawień maszyny ani gwarantowanego uzysku.
  Potwierdzono 43 projekcje wyświetlania z fałszywie rozpoznanym poziomem ULV
  i bez zużywanych wejść. Planer odrzuca je także w starszych snapshotach.
  Jeden nowy dump zachowuje natywne ilości long, wymagania i bazowy uzysk.
  Wykonanie oraz poziom napięcia pozostają jawnie nierozwiązane. Wszystkie
  wcześniejsze tożsamości surowców i ich pola pozostają zgodne. Przechodzi
  183 testy Pythona. Nie zmieniono aktywnego snapshota ani głównego serwera.
- [x] Sprawdzić ograniczony sygnał innych niestandardowych projekcji maszyn.
  Census obejmuje 186917 rekordów GTRecipe i wskazuje 20 grup do oceny.
  Kod oraz rzeczywiste wyniki Fish Pond potwierdzają standardową obsługę
  losowych produktów. Nie ma podstaw do nowego wykluczenia. Pozostałe sygnały
  pozostają niezweryfikowane. Brak zużywanych wejść sam w sobie nie jest błędem.
- [x] Zmierzyć wpływ pozycji wyjścia w dwóch źródłowo potwierdzonych importach
  receptury Temporal comb. Żadna z nich nie trafia do oceny w ośmiu zapisanych
  zapytaniach. Nie wykonano pozornej zmiany ani nie uogólniono tego wyniku
  na wszystkie receptury Centrifuge. Przygotowanie kosztuje osobno 23 ms.
- [x] Zmierzyć powtarzanie identycznej oceny przejścia w obrębie zapytania.
  Najpierw policzyć dokładne argumenty i pozostały koszt po istniejących cache.
  Sprawdzić standardowe lru tylko przy istotnym koszcie. Oddzielić logiczne
  wywołania od faktycznych obliczeń. Zachować oceny, kolejność i kompletność
  wyników oraz limity pracy. Negatywny wynik kończy próbę bez nowego cache.
  86% wywołań dla casingu powtarza argumenty, ale pozostaje tylko około 5 ms
  oszczędności w profilu. Suma median ośmiu zapytań pogarsza się o 0,6%.
  Wszystkie wyniki i limity pozostają zgodne. Nie dodajemy kolejnego cache.
- [x] Sprawdzić jeden przykład spoza żelaza: Silicon Dust do zwykłego waferu.
  Najpierw odtworzyć konkretną drogę z natywnych receptur, potem wykonać jedno
  zapytanie z dotychczasowymi limitami. Zachować wszystkie współskładniki
  i wymagania poziomu receptury. Niejednoznaczny cel kończy próbę bez rozszerzania.
  Potwierdzono drogę czterech procesów przez Trichlorosilane i Solar Grade
  Silicon. Wynik pokazuje zamiast niej siedem kroków przez Dark Steel i młotek.
  Pokrywa wszystkie osiem formalnych gałęzi, ale ten wskaźnik nie opisuje
  użyteczności wybranej historii. Zachowano poprawność natywnych przejść.
- [x] Ustalić konkretną przyczynę wyboru młotka w przykładzie Silicon Wafer.
  Najpierw rozłożyć ocenę dwóch zapisanych świadków i zebrać natywne dane
  materiałów oraz współskładników. Oddzielić legalność od preferencji.
  Nie zwiększać limitów ani nie wykluczać wszystkich narzędzi lub recyklingu.
  Tokeny oparte na natywnych składnikach i nieprzezroczystych nazwach są
  spłaszczone bez podstawy porównania. Jeden eksperyment zachowuje wagi,
  odzyskuje cztery bezpośrednie drogi dla wafla, ale gubi gałąź obwodu
  Volcanusa i prawie podwaja pracę LV Hull. Odrzucono go bez dalszego strojenia.
- [x] Sprawdzić, czy deklaracja dopasowania konkretnego wejścia z młotkiem
  pozwala opisać jego kategorię narzędzia w starszym snapshotcie. Zweryfikować
  pięć kotwic jednego slotu, jedną natywną grupę i rzeczywisty kontrakt Forge.
  Oddzielić dowód kategorii dopasowania od dosłownego członkostwa, natywnego
  odczytu Ore IDs i faktycznego zużycia. Bez zmiany oceny przed tym dowodem.
  Wszystkie pięć kotwic jest w grupie HardHammer. Wybrany wariant z NBT
  pasuje do kotwicy r3688 przez rzeczywisty predykat ignorujący NBT.
  Potwierdzono Forge 1614 i pasywny getter GT .221. Możliwa podstawa
  declared_input_anchor_category jest kontekstowa, nie jest natywnym Ore IDs.
- [x] Wybrać minimalny interfejs dowodu kategorii dopasowanego składnika
  w istniejącym właścicielu. Sprawdzić dostępność kotwicy w przygotowanych
  relacjach i koszt wyszukiwania. Zachować osobną podstawę informacji,
  źródłowy proces, slot, wybór i grupę. Nie przesłaniać obecnego pustego,
  błędnego ani niepoprawnego pola natywnego. Bez nowego magazynu danych.
  Wybrano dowód kontekstowy z istniejących relacji. Gorąca ocena potrzebowałaby
  dodatkowej operacji w obecnym matcherze. Użytkownik polecił nie skupiać się
  na narzędziach. Wątek odłożony bez implementacji ani eksperymentu oceny.
- [x] Sprawdzić dokładnie powtarzające się wymagania produktu docelowego
  w dziewięciu zapisanych przypadkach. Oddzielić różne receptury od tego
  samego wymagania półproduktu. Zachować ich ilości, predykaty i pełne konteksty.
  Nie powtarzać odrzuconego wyboru ośmiu tras z większej puli dwunastu.
  Wafle mają osiem formalnych zadań i pięć dokładnych klas wymagań.
  Volcanus ma piętnaście zadań i dziewięć klas. W odrzuconym eksperymencie
  obwód znika z klas 7/9 do 6/9, choć formalne pokrycie nadal wynosi 10/15.
  Potwierdzono 43 wywołania matchera i 3906 kandydatów. Ilości 1/2 nie są
  łączone. Równość zbiorów dla exact/unified dotyczy tylko tego snapshota.
- [x] Sprawdzić, jak dopuścić różne drogi wcześniejszego przetwarzania
  tego samego półproduktu bez zwiększania limitów wyników ani pracy.
  Wykorzystać istniejące kursory i planowanie gałęzi. Zachować istotną drogę
  przez stal oraz gałęzie obwodu, casingu i pozostałe kontrole.
  Jedna próba zachowuje odrębne historie i kursory każdego zadania.
  Przy powtórzonym prefiksie pozwala na jedną dalszą ukończoną drogę.
  Grupowanie ogranicza do identycznych deklaracji slotów. Limity i ocena
  pozostają bez zmian. Dominacja stanów może już wcześniej odrzucić alternatywę.
  Jedna próba zwraca sześć zamiast ośmiu dróg wafla, nadal pokrywając 5/5
  klas wymagań. Nowy prefiks zmienia tylko producenta tej samej sekwencji
  materiałów. Droga chemiczna nadal nie występuje. Praca rośnie o 917 jednostek.
  Osiem kontroli zachowuje ścieżki. Nie wdrożono zmiany ani dalszego strojenia.
- [x] Ustalić dokładny klucz dominacji stanów oraz warunek odrzucania
  alternatyw. Sprawdzić, czy rozróżnia koszt, liczbę kroków i historię
  dalszej ścieżki. Najpierw analiza kodu i dwóch zapisanych świadków.
  Nie nazywać potencjalnego odrzucenia udowodnionym bez konkretnego zdarzenia.
  Klucz obejmuje zasób i spełnione wymagania. Historię zasobów jako zbiór
  dodaje tylko przy wymaganych materiałach. Historia receptur nie jest w kluczu.
  Zachowuje niedominowane pary koszt/liczba kroków, ale z równych tylko pierwszą.
  Dwa zapisane warianty formowania Solar Grade mają równy stan. Analiza kodu
  i zwrócony świadek potwierdzają zlanie konkretnego wariantu, nie wszystkich
  chemicznych prefiksów. Nie wykonano nowego zapytania ani zmiany silnika.
- [x] Sprawdzić jedną próbę podziału wyników według odrębnych wymagań celu.
  Dać jeszcze niepokrytej klasie wymagania szansę przed powtórzeniem tej samej
  klasy przez inną recepturę końcową. Zachować osobne kolejki i historie.
  Policzyć grupowanie i planowanie. Nie zwiększać limitów ani puli kandydatów.
  Dziewięć ustalonych przypadków musi zachować gałęzie obwodu, casingu i stali.
  Volcanus ma 8/9 zamiast 7/9 klas, ale nowa droga wchodzi przez młotek,
  a nadal wymaga dwóch gotowych płyt Hastelloy-N. Nie dowodzi produkcji płyt.
  Nie zgubiono klas ani starych prefiksów. Łączna praca dziewięciu oddzielnych
  zapytań rośnie 79184 do 111471. Grupowanie na żywo nie trafia do produkcji.
  Obecny rebuild ma dane do przygotowania klas offline. To nie rozwiązuje
  samo w sobie jakości konstrukcyjnej nowych dróg.
- [x] Sprawdzić kontrakt alternatywnych dróg i minimalny ogólny przykład
  odrzucenia przez dominację historii. Oddzielić brak wariantu od błędnej trasy.
  Sześć zasobów i pięć receptur odtwarza zgubienie lepiej ocenianej drogi.
  Obecny silnik zwraca p/u/f. Prywatny klucz pełnych historii zwraca p/r/q/u/f.
  Pełny rekord p i jego drugi składnik x pozostają identyczne. Nie jest to
  dowód kompletnego planu produkcji. Produkcja i snapshoty pozostają bez zmian.
- [x] Porównać reguły zachowywania alternatyw z dwiema pracami źródłowymi
  o najkrótszych prostych ścieżkach. Oddzielić graf przejść od pełnych wymagań
  AND/OR receptur. Bez nowego prototypu przed konkretną diagnozą.
  Przeczytano i sprawdzono pracę Eppsteina. Dopuszcza cykle, więc nie daje
  gwarancji dla naszego wyszukiwania prostych ścieżek. Pracy Yena nie udało się
  pobrać po 403 i zablokowanych przeglądarkach. Drugi tekst pozostaje nieczytany.
  Przydatny punkt odniesienia to odrębne historie i zachowana kolejka alternatyw.
- [x] Sprawdzić jedną prywatną próbę dominacji uwzględniającej dozwolone
  kontynuacje. Tańszy stan może odrzucić drugi tylko przy nie większej liczbie
  kroków i podzbiorze jego zablokowanych zasobów oraz receptur. Policzyć koszt
  historii i porównań. Zachować obecne limity oraz dziewięć ustalonych kontroli.
  Predykat naprawia mały przykład. Implementacja skanująca kubełki historii
  dobija limit pracy w pięciu przypadkach i gubi drogi. Nie odzyskuje żadnej
  nowej natywnej trasy. Zachowane rekordy są poprawne. Nie wdrożono zmiany.
  Koszt rezerwacji porównań jest odrębny od czasu i przyjęć do kolejki.
  Wynik nie dowodzi niemożliwości szybszego indeksowania historii.
- [x] Sprawdzić jedną połączoną próbę ostrożnego porównania podstaw danych
  materiałowych i planowania odrębnych wymagań celu. Wcześniejsza pierwsza
  zmiana odzyskiwała chemię krzemu, ale gubiła obwód Volcanusa na rzecz
  powtórzonej klasy Computer Cube. Druga może zapobiec tej konkretnej utracie.
  Policzyć oba koszty przygotowania. Bez zmiany wag, limitów ani historii.
  Odzyskano czteroetapowy prefiks chemiczny czterech wariantów wafla i zachowano
  obwód oraz konstrukcyjne prefiksy Volcanusa. Pierwsza droga wafla nadal jest
  gałęzią chłodziwa. Nie podniesiono limitów. Pozostałe siedem kontroli zachowuje
  uporządkowane drogi. Metadane na żywo kosztują za dużo. LV hull nadal przyjmuje
  1971 zamiast 912 stanów bez lepszego wyniku. Samo rozwijanie poprzedników
  rośnie łącznie o około 3,4%. Wariant dynamiczny nie trafia do produkcji.
- [x] Przygotować te same podstawy materiałowe i dokładne klasy wymagań
  offline w obecnym właścicielu indeksu. Bez drugiego magazynu semantycznego.
  Format 4 wymaga jawnej zwykłej odbudowy. Oryginalne rekordy pozostają pełne.
  Implementacja przechodzi 25 testów indeksu i 187 testów Pythona. Wyjaśnienia
  korzystają z tej samej oceny danych co ranking i leniwie czytają tylko zasoby
  wybranych ścieżek. Dziewięć zapytań zachowuje drogi i pełne rekordy próby
  połączonej. Pięć wyjaśnień wafla poprawnie przechodzi na niepełne dane.
  Odbudowa zajmuje 42,53 sekundy, indeks 133861376 bajtów. Matcher ma 74159
  unikalnych wywołań bez powtórzeń. Praca dziewięciu zapytań spada z 437921
  jednostek prototypu do 83818, z czego 1932 to planowanie klas. To nie dowód
  przyspieszenia czasu. HTTP i świeży stdio MCP przechodzą na kopii po końcowej
  poprawce liczników. Rozpoznane klasy i niepewne zadania są liczone osobno.
  Aktywne pliki, konfiguracje i usługi nie są przełączane.
- [x] Zaproponować grupy artefaktów wyłączanych z pośrednich kroków chaina.
  Użytkownik wskazał narzędzia i części Tinkersa oraz narzędzia GregTecha.
  Wytwarzanie pozostaje dostępne przy bezpośrednio wybranym celu. Wymagane
  składniki pełnych receptur pozostają widoczne. Najpierw dowody kategorii
  i krótka lista grup, bez hurtowej listy itemów ani klasyfikacji po nazwach.
  Dodatkowe grupy i niejednoznaczne przemysłowe warianty wymagają osobnej oceny.
  Sprawdzono natywne rejestracje ToolCore/IToolPart oraz metadane GT i osobne
  rejestry Detrav/Toolbox. TGregworks części wchodzą w IToolPart. Rejestr GT
  obejmuje też rotory turbin, a ToolCore Tinkersa amunicję. Nie zawężono
  polecenia użytkownika do narzędzi ręcznych bez zaznaczenia tej propozycji.
  Dodatkowe kandydaty to jednorazowe przyrządy, formy/szablony i zbroje gracza.
  GGfab produkuje 64 młotki z 432 jednostek stopionej stali, więc nie są
  rzadkim wyposażeniem. Brak hurtowej listy ID.
  Użytkownik potwierdził, że rotory turbin też mają być tylko bezpośrednim celem.
  Nie wprowadzamy dla nich rekomendowanego wcześniej wyjątku.
  Użytkownik potwierdził też amunicję Tinkersa jako bezpośredni cel.
- [x] Wdrożyć rozpoznawanie tych rodzin przez pasywnie przechwyconą hierarchię
  klas i interfejsów itemu. Przygotować fakty w istniejącym indeksie przepływu
  i dodać jawny tryb ograniczania pośrednich narzędzi. Zachować crafting celu,
  pełne wymagania receptur oraz nieograniczony audyt i recykling.
  Nie zastępować brakującej hierarchii nazwami itemów ani listą ID.
  Sprawdzić nowy capture przed zmianą ustawienia domyślnego.
  Wdrożono opcję `terminal_artifact_policy` w silniku, HTTP, MCP, CLI i GUI.
  Indeks wersji 5 przechowuje klasyfikację. Przechodzi 194 testy Pythona,
  67 GUI i 32 Javy. Jeden capture `.225` potwierdza 117299 pełnych hierarchii
  bez błędów oraz zgodność wszystkich przygotowanych kategorii.
  Jest 21212 wariantów narzędzi GT i 32609 części. Zwykłe rotory, formy oraz
  GGfab pozostają poza regułą. Gotowych narzędzi i amunicji Tinkersa nie ma
  w korpusie zasobów, więc ich dodatnie przykłady są tylko w testach i źródłach.
  Dziewięć ograniczonych zapytań natywnych potwierdza regułę i pełne wymagania.
  Po połączeniu po tożsamości wszystkie stare pola zasobów są identyczne.
  2282 różnice dotyczyły wyłącznie lokalnych ID. Wszystkie chronione pliki
  pozostają niezmienione. Brak ogólnego przyspieszenia: tryb shortest płaci
  za odczyt hierarchii, a material używa przygotowanych kategorii.
  Domyślnie pozostaje `allow`. Aktywnej bazy i usług nie przełączono.
  Dodatkowy preflight końców trasy odrzuca niemożliwe pary narzędzie/część
  do zwykłego lub nierozpoznanego celu przed rozwijaniem grafu. Wynika to
  z tej samej reguły przejść. Odczyty są płatne, a sprawdzenia końców są
  oddzielone od prawdziwych krawędzi. GUI wyjaśnia powód pustego wyniku.
  Przechodzi 84 testy skupione na kontrakcie oraz pełny zestaw GUI 68 testów.
  Nie powtarzano wcześniejszych dziewięciu zapytań natywnych.
- [ ] Sprawdzić opcjonalną natywną historię rejestracji receptur jako dowód
  roli wejść Cuttera. GT udostępnia `GTRecipe.stackTraces`, ale historia może
  zniknąć przy kopiowaniu i jej zbieranie obejmuje całą paczkę. Oddzielny
  eksperyment ma zmierzyć koszt inicjalizacji i pamięci. Nie włączamy tej
  opcji w capture sprawdzającym klasy itemów ani nie zgadujemy ról po nazwach.
  Dodano osobny opcjonalny eksport i jedną próbę natywną. Kod i kodowanie
  przechodzą sprawdzenia, ale limit 128 MiB kończy się przed Cutterem.
  Cztery sprawdzane wafle nie mają użytecznych śladów, więc nie wdrażamy
  klasyfikacji roli wejść. Brak podniesienia limitu i powtórki dumpa.
  Porównanie wszystkich uporządkowanych receptur też nie daje pełnej zgodności.
  Snapshot pozostaje badawczy. Pomiar pokazuje 8340537344 bajtów szczytowego
  working set gry, bez pomiaru bazowego do obliczenia narzutu.
  Kolejna hipoteza offline dotyczy współdzielenia powtarzanych śladów.
- [x] Sprawdzić literaturę o landmarkach i planach zrelaksowanych pod kątem
  kierowania przez gałęzie składników celu. Odróżnić osiągalność pojedynczej
  ścieżki od spełnienia wszystkich wejść receptury i policzyć przygotowanie.
  Literatura uzasadnia warunkową mapę AND/OR dla istniejącego planera granic.
  Próba zatrzymała się przed eksperymentem, bo snapshot nie ma żadnego profilu
  surowców wejściowych. Nie wymyślono zapasów, nie wykonano ani nie oceniono
  mapy. Powrót do pilota wymaga jawnego profilu przez istniejący interfejs.
- [x] Sprawdzić wybieranie wyjść regionu na podstawie rzeczywistych gałęzi
  celu i przygotowanych odległości. Policzyć przygotowanie, konkretne kroki,
  walidację i pracę zapytania. Odrzucić rozwiązanie, jeśli wyjścia pozostaną
  liczne albo dopracowanie świadków zużyje oszczędność.
  Wyjścia początkowych regionów pozostają liczne. Oszczędność 291 sprawdzeń
  relacji nie pokrywa 4747 nowych sprawdzeń granic ani przygotowania. Zachowano
  wszystkie 18 badanych kontynuacji, ale nie promujemy tej selekcji do silnika.
- [x] Sprawdzić zgodność profilu ilości GT `.221` z faktycznie pobranym
  `.223`. Nowy dump zachowuje nierozwiązane bilanse i pozostaje odrębny.
  Użycie go do analiz chemicznych wymaga dowodów zgodności, bez osłabiania
  kontroli i bez zerwania wsparcia dla działającego snapshota `.221`.
  Dodano dokładną listę dwóch obsługiwanych wersji. Nowy odrębny capture
  potwierdza identyczne wektory i podstawy ilości dla 4695 obsługiwanych
  tożsamości. Wcześniejszy nierozwiązany dump `.223` nie został zmieniony.
  Przechodzi 170 testów Pythona i 30 testów Javy.

Każda próba ma podać wynik negatywny, jeśli nie poprawia jakości lub pokrycia.
Nie zwiększamy limitów, żeby ukryć brak kierunku wyszukiwania. Rozpoznanie
materialnego obiegu nie upoważnia do usuwania receptur z audytu loopów.
