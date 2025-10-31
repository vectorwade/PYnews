# Metropoles Scraper (exemplo)

Este repositório contém um scraper simples e organizado (DDD-friendly) para extrair as principais notícias de categorias e gerar um CSV agregando título, resumo e link.

Implementação atual: Selenium WebDriver (usuário pediu `selenium`). O script usa `webdriver-manager` para baixar automaticamente os drivers no Windows.

## Requisitos
- Python 3.8+
- pip

## Instalação (PowerShell)

```powershell
python -m pip install -r requirements.txt
```

## Uso (exemplo)

```powershell
python scraper.py --browser chrome --limit 5 --headless
```

Parâmetros principais:
- `--browser`: chrome|firefox
- `--limit`: número máximo de itens por categoria (padrão 5)
- `--categories`: lista de category names or URLs separados por vírgula. Se nomes (ex.: "Últimas notícias, Brasil") o scraper tentará achá-los na homepage.
- `--categories-file`: arquivo de texto com uma URL ou nome por linha
- `--headless`: flag para rodar sem UI

## Notas importantes
- O script tenta localizar links de categorias a partir da homepage `https://www.metropoles.com/` usando o texto dos links. Se preferir, passe URLs diretas via `--categories` ou `--categories-file`.
- `webdriver-manager` baixa drivers automaticamente. Em ambiente restrito (sem internet), você precisará instalar o driver manualmente e garantir que esteja no PATH.

## Exemplo rápido (PowerShell)

```powershell
python -m pip install -r requirements.txt
python scraper.py --browser chrome --limit 5 --headless
```

Se quiser que eu gere exemplos de `--categories` já preparados (lista de nomes das categorias solicitadas), eu posso acrescentar um arquivo `categories.txt` com esses valores.

## Arquivo `categories.txt`

Você pode também fornecer um arquivo `categories.txt` com uma linha por categoria — o script aceitará nomes (ex.: "Brasil") ou URLs completas. Um exemplo já foi incluído em `categories.txt` com as categorias solicitadas.

Exemplo de uso com arquivo de categorias:

```powershell
python scraper.py --browser chrome --limit 5 --categories-file categories.txt --headless
```