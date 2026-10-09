# TODO Radar — encontre TODOs e FIXMEs esquecidos no seu código (Python)

Todo projeto acumula `TODO: arrumar depois` que ninguém arruma. O **todo-radar** varre o código, encontra as marcações dentro dos comentários (TODO, FIXME, HACK, XXX, BUG e OPTIMIZE) e usa o `git blame` para mostrar quem escreveu cada uma e há quanto tempo, das mais antigas para as mais novas. Dá para gerar uma tabela em Markdown para uma issue, um JSON para scripts ou fazer o CI falhar quando aparecer uma marcação velha demais.

Funciona em qualquer pasta (com ou sem git), entende os comentários de dezenas de linguagens e não tem dependências além do Python.

## Recursos

- Procura **TODO, FIXME, HACK, XXX, BUG e OPTIMIZE** (ou as marcações que você quiser, com `--tags`).
- Só olha dentro de comentários: `#`, `//`, `/* */` (inclusive em várias linhas), `<!-- -->`, `--`, `;`, `%` e `'` (VB), de acordo com a extensão do arquivo.
- Aceita `TODO: texto`, `TODO texto` e `TODO(maria): texto` (o nome entre parênteses aparece junto da marcação).
- Em repositórios git, usa o `git ls-files` (respeita o `.gitignore`) e o `git blame --line-porcelain` uma vez por arquivo com marcações, para saber o autor e a data de cada linha.
- Fora do git, ou para linhas ainda não commitadas, usa a data de modificação do arquivo.
- Pula binários, arquivos com mais de 2 MB e pastas como `node_modules`, `venv`, `.venv`, `dist`, `build`, `vendor` e `__pycache__`.
- Tabela no terminal ordenada da mais antiga para a mais nova, com idade em português ("há 3 meses").
- `--agrupar arquivo|tag|autor`, `--markdown`, `--json`, `--mais-velho-que 90d` e `--falhar-se-encontrar` para CI.

## Instalação

```bash
pipx install git+https://github.com/micdog22/todo-radar
# ou
pip install git+https://github.com/micdog22/todo-radar
```

Requer Python 3.9 ou mais novo. O git é opcional: sem ele, a ferramenta funciona sem autor e com a idade estimada pela data dos arquivos.

## Como usar

Na pasta do projeto:

```console
$ todo-radar
LOCAL              TAG         AUTOR            IDADE        TEXTO
src/clientes.py:2  TODO(joao)  Maria Exemplo    há 2 anos    validar o CPF antes de salvar
web/frete.js:3     HACK        João Exemplo     há 10 meses  tabela fixa até a API de frete voltar
web/frete.js:5     XXX         João Exemplo     há 10 meses  valor provisório
web/index.html:2   FIXME       João Exemplo     há 10 meses  o menu quebra no celular
src/schema.sql:1   BUG         (não commitado)  hoje         índice duplicado na tabela de pedidos

5 marcações em 4 arquivos (TODO 1, HACK 1, XXX 1, FIXME 1, BUG 1).
```

Agrupado por arquivo (ou por `tag` ou `autor`):

```console
$ todo-radar --agrupar arquivo
LOCAL              TAG         AUTOR            IDADE        TEXTO

src/clientes.py (1)
src/clientes.py:2  TODO(joao)  Maria Exemplo    há 2 anos    validar o CPF antes de salvar

web/frete.js (2)
web/frete.js:3     HACK        João Exemplo     há 10 meses  tabela fixa até a API de frete voltar
web/frete.js:5     XXX         João Exemplo     há 10 meses  valor provisório
...
```

Só o que está esquecido há mais de 6 meses, em Markdown para colar numa issue:

```console
$ todo-radar --mais-velho-que 6m --markdown
| Local | Tag | Autor | Idade | Texto |
|---|---|---|---|---|
| `src/clientes.py:2` | TODO(joao) | Maria Exemplo | há 2 anos | validar o CPF antes de salvar |
| `web/frete.js:3` | HACK | João Exemplo | há 10 meses | tabela fixa até a API de frete voltar |
| `web/frete.js:5` | XXX | João Exemplo | há 10 meses | valor provisório |
| `web/index.html:2` | FIXME | João Exemplo | há 10 meses | o menu quebra no celular |

4 marcações em 3 arquivos (TODO 1, HACK 1, XXX 1, FIXME 1).
```

Outros exemplos:

```bash
todo-radar ~/projetos/loja                 # outra pasta
todo-radar --tags TODO,FIXME,REVISAR       # suas próprias marcações
todo-radar --json > marcacoes.json         # para scripts e painéis
todo-radar --sem-git                       # ignora o git (mais rápido em repositórios enormes)
```

### Opções

| Opção | O que faz |
|---|---|
| `--tags LISTA` | marcações procuradas, separadas por vírgula (padrão: `TODO,FIXME,HACK,XXX,BUG,OPTIMIZE`) |
| `--agrupar arquivo\|tag\|autor` | agrupa o resultado |
| `--markdown` | tabela em Markdown |
| `--json` | resultado em JSON (com `arquivo`, `linha`, `tag`, `responsavel`, `texto`, `autor`, `data`, `idade_dias`, `idade` e `origem`) |
| `--mais-velho-que IDADE` | só marcações mais antigas que `IDADE`: `90d` (dias), `2s` (semanas), `6m` (meses de 30 dias) ou `1a` (anos de 365 dias) |
| `--falhar-se-encontrar` | sai com código 1 se sobrar alguma marcação depois dos filtros |
| `--sem-git` | não usa o git |

Códigos de saída: `0` ok, `1` marcações encontradas com `--falhar-se-encontrar`, `2` uso incorreto.

### No CI

Para barrar marcações com mais de um ano no GitHub Actions. O `fetch-depth: 0` é importante: sem o histórico completo, o `git blame` atribui tudo ao último commit.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- name: TODOs esquecidos
  run: |
    pipx install git+https://github.com/micdog22/todo-radar
    todo-radar --mais-velho-que 1a --falhar-se-encontrar
```

## Como funciona

- **Onde procurar:** a marcação precisa ser a primeira palavra de um comentário (depois de `#`, `//`, `/*`, `*`, `<!--`, `--`, `;`, `%`, `'`, `REM` ou `::`, conforme a linguagem), em maiúsculas e seguida de `:`, espaço, `(` ou fim de linha. Assim, frases como `# Todo cliente tem CPF`, `# veja o TODO acima` ou `TODOS` não são confundidas com marcações. Em português isso importa: "todo" é palavra comum.
- **Linguagens:** a extensão do arquivo define os comentários válidos (Python e shell usam `#`; JavaScript, TypeScript, Java, C, C#, Go, Rust, Kotlin e Swift usam `//` e `/* */`; HTML, XML e Markdown usam `<!-- -->`; SQL e Lua usam `--`; Lisp, Clojure e INI usam `;`; LaTeX e Erlang usam `%`; VB usa `'`; `.bat` usa `REM` e `::`). Arquivos de tipo desconhecido usam um conjunto genérico, sem o apóstrofo do VB.
- **Autor e idade:** em repositórios git, a lista de arquivos vem do `git ls-files --cached --others --exclude-standard` e cada arquivo com marcações passa uma vez pelo `git blame --line-porcelain`. Linhas ainda não commitadas e arquivos novos aparecem como "(não commitado)", com a data de modificação do arquivo.
- **Texto:** arquivos em UTF-8 e em cp1252/latin-1 (comum em código legado brasileiro) são lidos corretamente.

## Rodando a partir do código-fonte

```bash
git clone https://github.com/micdog22/todo-radar
cd todo-radar
PYTHONPATH=src python3 -m todo_radar /caminho/do/seu/projeto
```

## Testes

```bash
python3 -m unittest discover -s tests -v
```

Os testes de integração criam um repositório git temporário com autores e datas fixos (e são pulados se o git não estiver instalado).

## Contribuindo

Issues e pull requests são bem-vindos, principalmente com linguagens que ainda não são reconhecidas.

## Licença

MIT — veja [LICENSE](LICENSE).
