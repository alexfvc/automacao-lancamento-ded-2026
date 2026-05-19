import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

SITE_URL   = "https://dedmais.educacao.mg.gov.br/"
EXCEL_FILE = "planejamento.xlsx"


# ── Dados ────────────────────────────────────────────────────────────────────

def carregar_tabela():
    tabela = pd.read_excel(EXCEL_FILE, sheet_name="preencher")
    tabela["Data"] = pd.to_datetime(tabela["Data"], dayfirst=True, errors="coerce") \
                       .dt.strftime("%d/%m/%Y")
    return tabela


# ── Browser ──────────────────────────────────────────────────────────────────

def iniciar_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,900")
    return webdriver.Chrome(options=options)


def aguardar_login(driver):
    driver.get(SITE_URL)
    time.sleep(3)
    url = driver.current_url.lower()
    if "login" in url or "auth" in url:
        print("[!] Sessão não detectada. Faça login manualmente e pressione Enter...")
        input()
        time.sleep(2)
    print("[OK] Login confirmado.\n")


def wait_for(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


# ── Scraping: lista de turmas ─────────────────────────────────────────────────

def carregar_cards(driver):
    """
    Faz scroll para disparar lazy loading e retorna lista paralela aos elementos
    .v-card-text do DOM. Entradas sem dados suficientes ficam como None para
    preservar o mapeamento de índice usado no clique posterior.
    """
    print("[*] Carregando lista de turmas...")
    try:
        wait_for(driver, By.CLASS_NAME, "v-card-text")
    except TimeoutException:
        print("[!] Nenhum card encontrado na página.")
        return []

    ultima_altura = driver.execute_script("return document.body.scrollHeight")
    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        nova_altura = driver.execute_script("return document.body.scrollHeight")
        if nova_altura == ultima_altura:
            break
        ultima_altura = nova_altura
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    cards_info = []
    for card in driver.find_elements(By.CLASS_NAME, "v-card-text"):
        try:
            linhas = card.text.splitlines()
            if len(linhas) >= 5:
                cards_info.append({
                    "turma":      linhas[1].split(" - ")[0].strip(),
                    "disciplina": linhas[3].strip(),
                    "turno":      linhas[4].strip(),
                })
            else:
                cards_info.append(None)
        except Exception:
            cards_info.append(None)

    validos = sum(1 for c in cards_info if c)
    print(f"[*] {validos} cards válidos de {len(cards_info)} encontrados.\n")
    return cards_info


# ── Scraping: aulas já lançadas ───────────────────────────────────────────────

def obter_aulas_existentes(driver):
    """
    Lê os cards .v-card.my-2 da aba Aulas e retorna set de datas DD/MM
    já lançadas. Retorna set vazio se a aba não tiver nenhuma aula.
    """
    existentes = set()
    try:
        wait_for(driver, By.CSS_SELECTOR, ".v-card.my-2", timeout=10)
    except TimeoutException:
        return existentes

    time.sleep(0.5)
    for card in driver.find_elements(By.CSS_SELECTOR, ".v-card.my-2"):
        try:
            h3_els = card.find_elements(By.TAG_NAME, "h3")
            if not h3_els:
                continue
            m = re.match(r"^(\d{2}/\d{2})(?:/\d{4})?", h3_els[0].text.strip())
            if m:
                existentes.add(m.group(1))
        except StaleElementReferenceException:
            continue
    return existentes


# ── Lançamento ────────────────────────────────────────────────────────────────

def find_button_by_text(driver, text):
    for btn in driver.find_elements(By.CLASS_NAME, "v-btn"):
        if btn.text.strip().lower() == text.strip().lower():
            return btn
    return None


def clicar_aba_aulas(driver):
    """
    Localiza o botão laranja 'Aulas' pelo wrapper que contém o texto,
    com fallback para o único .bg-orange da página.
    """
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.v-btn.bg-orange"))
        )
        for wrapper in driver.find_elements(By.CSS_SELECTOR, "div.d-flex.flex-column.align-center"):
            if wrapper.text.strip() == "Aulas":
                btn = wrapper.find_element(By.CSS_SELECTOR, "button.v-btn.bg-orange")
                driver.execute_script("arguments[0].click();", btn)
                return True
        btn = driver.find_element(By.CSS_SELECTOR, "button.v-btn.bg-orange")
        driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception as e:
        print(f"    [!] Botão Aulas não encontrado: {e}")
        return False


def lancar_aula(driver, data, conteudo):
    """
    Lança uma única aula:
    Cadastrar aula → preencher data (TAB para fechar datepicker)
    → conteúdo → Salvar → Cancelar.
    Todos os cliques em botões via execute_script para evitar overlays.
    """
    btn = find_button_by_text(driver, "Cadastrar aula") or \
          driver.find_elements(By.CLASS_NAME, "v-btn")[2]
    driver.execute_script("arguments[0].click()", btn)
    time.sleep(1)

    campo_data = driver.find_element(By.ID, "dataAula")
    campo_data.click()
    time.sleep(0.5)
    for _ in range(10):
        campo_data.send_keys(Keys.BACKSPACE)
    campo_data.send_keys(str(data))
    time.sleep(0.5)
    campo_data.send_keys(Keys.TAB)
    time.sleep(0.5)

    textarea = driver.find_element(
        By.XPATH,
        "/html/body/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[6]/textarea"
    )
    textarea.send_keys(conteudo)
    time.sleep(1)

    btn = find_button_by_text(driver, "Salvar") or \
          driver.find_elements(By.CLASS_NAME, "v-btn")[9]
    driver.execute_script("arguments[0].click()", btn)
    time.sleep(1)

    btn = find_button_by_text(driver, "Cancelar") or \
          driver.find_elements(By.CLASS_NAME, "v-btn")[8]
    driver.execute_script("arguments[0].click()", btn)
    time.sleep(1)


# ── Orquestrador ──────────────────────────────────────────────────────────────

def processar_turmas(driver, tabela):
    driver.get(SITE_URL)
    time.sleep(2)

    cards_info = carregar_cards(driver)
    if not cards_info:
        print("[!] Nenhuma turma encontrada. Encerrando.")
        return

    n = len(cards_info)

    for i, meta in enumerate(cards_info):
        if meta is None:
            continue

        turma_card = meta["turma"]
        disc_card  = meta["disciplina"]

        filtro = (tabela["Turma"] == turma_card) & (tabela["Disciplina"] == disc_card)
        aulas  = tabela[filtro].copy()

        if aulas.empty:
            print(f"  [{i+1}/{n}] {turma_card[:55]} -> sem aulas no Excel, pulando.")
            continue

        print(f"\n[{i+1}/{n}] {turma_card} | {disc_card} -> {len(aulas)} aula(s) no Excel")

        try:
            # volta à lista e clica no card pelo índice (paralelo a cards_info)
            driver.get(SITE_URL)
            time.sleep(2)
            wait_for(driver, By.CLASS_NAME, "v-card-text", timeout=15)
            cards_atuais = driver.find_elements(By.CLASS_NAME, "v-card-text")
            if i >= len(cards_atuais):
                print(f"    [!] Card {i} não encontrado na página, pulando.")
                continue
            driver.execute_script("arguments[0].click();", cards_atuais[i])
            time.sleep(2)

            # abre aba Aulas
            if not clicar_aba_aulas(driver):
                print(f"    [!] Não foi possível abrir aba Aulas, pulando.")
                continue
            time.sleep(2)

            # scraping: aulas já lançadas no site para esta turma
            ja_lancadas = obter_aulas_existentes(driver)
            print(f"   [DIAG] No site: {sorted(ja_lancadas) if ja_lancadas else 'nenhuma aula lançada'}")

            # remove datas duplicadas de ambas as tabelas antes de lançar
            mask_dup = aulas["Data"].str[:5].isin(ja_lancadas)
            if mask_dup.any():
                datas_dup = sorted(aulas.loc[mask_dup, "Data"].tolist())
                idx_dup   = aulas[mask_dup].index.tolist()
                print(f"   [DIAG] Ja lancadas, removendo de ambas as tabelas ({len(datas_dup)}): {datas_dup}")
                aulas = aulas[~mask_dup].reset_index(drop=True)
                tabela.drop(index=idx_dup, inplace=True)
            else:
                aulas = aulas.reset_index(drop=True)

            if aulas.empty:
                print(f"   Todas as aulas ja foram lancadas, pulando.")
                continue

            print(f"   Lancando {len(aulas)} aula(s) nova(s)...")
            for _, row in aulas.iterrows():
                print(f"   [+] {row['Data']}: {str(row['ConteudoLecionado'])[:60]}...")
                lancar_aula(driver, row["Data"], row["ConteudoLecionado"])

            print(f"   Resultado: {len(aulas)} lancada(s).")

        except Exception as e:
            print(f"    [ERRO] {turma_card}: {str(e)[:120]}")
            driver.get(SITE_URL)
            time.sleep(3)
            continue

    print("\n=== LANCAMENTO CONCLUIDO ===")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tabela = carregar_tabela()
    print(f"[*] Planilha carregada: {len(tabela)} linhas")
    resumo = tabela.groupby(["Turma", "Disciplina"]).size().reset_index(name="Aulas")
    for _, r in resumo.iterrows():
        print(f"    {r['Turma']} | {r['Disciplina']} ({r['Aulas']} aulas)")
    print()

    driver = iniciar_browser()
    try:
        aguardar_login(driver)
        resp = input("Iniciar lancamento? (s/n): ")
        if resp.lower() == "s":
            processar_turmas(driver, tabela)
        else:
            print("Cancelado.")
    finally:
        input("\nPressione Enter para fechar o browser: ")
        driver.quit()
