import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

SITE_URL    = "https://dedmais.educacao.mg.gov.br/"
EXCEL_FILE  = "planejamento.xlsx"


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def carregar_dados():
    tabela = pd.read_excel(EXCEL_FILE, sheet_name="preencher")
    tabela["Data"] = tabela["Data"].dt.strftime("%d/%m/%Y")

    turmas_materias = pd.read_excel(EXCEL_FILE, sheet_name="Turmas e materias")
    turmas_materias.columns   = turmas_materias.columns.str.strip()
    turmas_materias["turmas"]   = turmas_materias["turmas"].str.strip()
    turmas_materias["materias"] = turmas_materias["materias"].str.strip()
    turmas_materias["Turno"]    = turmas_materias["Turno"].str.strip()

    return tabela, turmas_materias


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

def iniciar_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(options=options, service=service)


def login(driver):
    print("Abrindo o diário eletrônico...")
    driver.get(SITE_URL)
    print("Preencha login, senha e CAPTCHA no browser. NÃO clique em Entrar.")
    input("Pressione Enter aqui quando terminar: ")
    try:
        driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div/div/div[1]/div[4]/div[3]/div/div[1]/div/form/div[4]/button[2]"
        ).click()
    except Exception:
        pass
    time.sleep(3)
    print("Login concluído.\n")


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------

def diagnostico(driver, turmas_materias):
    cards = driver.find_elements(By.CLASS_NAME, "v-card-text")
    print("=" * 60)
    print(f"  CARDS NO SITE  ({len(cards)} encontrados)")
    print("=" * 60)

    site_data = []
    for i, card in enumerate(cards):
        linhas = card.text.splitlines()
        if len(linhas) >= 5:
            turma = linhas[1].split(" - ")[0].strip()
            disc  = linhas[3].strip()
            turno = linhas[4].strip()
            site_data.append({"turmas": turma, "materias": disc, "Turno": turno})
            print(f"  [{i:02d}] {turma}  |  {disc}  |  {turno}")

    df_site = pd.DataFrame(site_data)

    print()
    print("=" * 60)
    print("  CORRESPONDÊNCIAS COM O EXCEL  (aba: Turmas e materias)")
    print("=" * 60)
    ok = 0
    nok = 0
    for _, row in turmas_materias.iterrows():
        match = not df_site[
            (df_site["turmas"]   == row["turmas"]) &
            (df_site["materias"] == row["materias"])
        ].empty
        if match:
            ok += 1
            status = "OK"
        else:
            nok += 1
            status = "NAO ENCONTRADO"
        print(f"  [{status}]  {row['turmas']}  |  {row['materias']}  |  {row['Turno']}")

    print()
    print(f"  Resumo: {ok} OK  |  {nok} sem correspondência no site")
    print("=" * 60)
    print()
    return ok, nok


# ---------------------------------------------------------------------------
# Lançamento
# ---------------------------------------------------------------------------

def obter_aulas_existentes(driver):
    """
    Lê os cards da página de aulas da turma atual e retorna um set
    com as datas já lançadas no formato DD/MM.

    Os cards de aulas existentes aparecem como "DD/MM | Copiar" ou
    "DD/MM/YYYY | ...". Ignora cards sem data (ex: "Chamada pendente").
    """
    existentes = set()
    cards = driver.find_elements(By.CLASS_NAME, "v-card-text")
    for card in cards:
        linhas = card.text.splitlines()
        if not linhas:
            continue
        # Procura data no formato DD/MM ou DD/MM/YYYY no início da linha
        match = re.match(r"^(\d{2}/\d{2})(?:/\d{4})?", linhas[0].strip())
        if match:
            existentes.add(match.group(1))  # guarda só DD/MM
    return existentes


def find_button_by_text(driver, text):
    for btn in driver.find_elements(By.CLASS_NAME, "v-btn"):
        if btn.text.strip().lower() == text.strip().lower():
            return btn
    return None


def lancamento(driver, data, conteudo):
    buttons = driver.find_elements(By.CLASS_NAME, "v-btn")
    btn = find_button_by_text(driver, "Cadastrar aula") or buttons[2]
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

    buttons = driver.find_elements(By.CLASS_NAME, "v-btn")
    btn = find_button_by_text(driver, "Salvar") or buttons[9]
    driver.execute_script("arguments[0].click()", btn)
    time.sleep(1)

    buttons = driver.find_elements(By.CLASS_NAME, "v-btn")
    btn = find_button_by_text(driver, "Cancelar") or buttons[8]
    driver.execute_script("arguments[0].click()", btn)
    time.sleep(1)


def select_turma(driver, tabela):
    driver.get(SITE_URL)
    time.sleep(3)
    cards = driver.find_elements(By.CLASS_NAME, "v-card-text")
    n_cards = len(cards)
    print(f"Total de cards: {n_cards}\n")

    for i in range(n_cards):
        turma_card      = f"card_{i}"
        disciplina_card = "?"
        try:
            cards = driver.find_elements(By.CLASS_NAME, "v-card-text")
            linhas = cards[i].text.splitlines()

            if len(linhas) < 5:
                continue

            turma_card      = linhas[1].split(" - ")[0].strip()
            disciplina_card = linhas[3].strip()

            filtro = (tabela["Turma"] == turma_card) & (tabela["Disciplina"] == disciplina_card)
            aulas  = tabela[filtro].copy()  # mantém índices originais para drop posterior

            if aulas.empty:
                print(f"  [{i:02d}] {turma_card} -> sem aulas, pulando.")
                continue

            print(f"\n[{i:02d}] {turma_card} | {disciplina_card} -> {len(aulas)} aula(s) no Excel")

            cards[i].click()
            time.sleep(1)
            driver.implicitly_wait(5)

            btn_aula = find_button_by_text(driver, "Aula")
            if btn_aula:
                btn_aula.click()
            else:
                driver.find_elements(By.CLASS_NAME, "v-btn")[4].click()
            time.sleep(1)
            driver.implicitly_wait(5)

            # Diagnóstico: remove de ambas as tabelas as datas já lançadas no site
            ja_lancadas = obter_aulas_existentes(driver)
            mask_dup = aulas["Data"].str[:5].isin(ja_lancadas)
            if mask_dup.any():
                datas_dup = sorted(aulas.loc[mask_dup, "Data"].tolist())
                idx_dup   = aulas[mask_dup].index.tolist()
                print(f"   [DIAG] Já lançadas no site ({len(datas_dup)}): {datas_dup}")
                aulas = aulas[~mask_dup].reset_index(drop=True)
                tabela.drop(index=idx_dup, inplace=True)
                print(f"   [DIAG] {len(datas_dup)} linha(s) removida(s) de ambas as tabelas.")
            else:
                aulas = aulas.reset_index(drop=True)

            if aulas.empty:
                print(f"   Nenhuma aula nova para lançar, pulando.")
                driver.get(SITE_URL)
                time.sleep(3)
                continue

            novas = 0
            for _, row in aulas.iterrows():
                print(f"   [+] {row['Data']}: {str(row['ConteudoLecionado'])[:60]}...")
                lancamento(driver, row["Data"], row["ConteudoLecionado"])
                novas += 1

            print(f"   Resultado: {novas} lançada(s).")
            driver.get(SITE_URL)
            time.sleep(3)
            driver.implicitly_wait(5)

        except Exception as e:
            print(f"  ERRO [{i:02d}] {turma_card}: {str(e)[:120]}")
            driver.get(SITE_URL)
            time.sleep(3)
            continue

    print("\n=== LANÇAMENTO CONCLUÍDO ===")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tabela, turmas_materias = carregar_dados()
    print(f"Tabela carregada: {len(tabela)} linhas")
    resumo = tabela.groupby(["Turma", "Disciplina"]).size().reset_index(name="Aulas")
    for _, r in resumo.iterrows():
        print(f"  {r['Turma']} | {r['Disciplina']} ({r['Aulas']} aulas)")
    print()

    driver = iniciar_browser()
    try:
        login(driver)

        ok, nok = diagnostico(driver, turmas_materias)
        if nok > 0:
            resp = input(f"{nok} turma(s) sem correspondência no site. Continuar mesmo assim? (s/n): ")
            if resp.lower() != "s":
                print("Cancelado.")
                driver.quit()
                exit()

        resp = input("Iniciar lançamento das aulas? (s/n): ")
        if resp.lower() == "s":
            select_turma(driver, tabela)
        else:
            print("Lançamento cancelado.")

    finally:
        input("\nPressione Enter para fechar o browser: ")
        driver.quit()
