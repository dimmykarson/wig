# Contribuindo com o wig

Obrigado pelo interesse em contribuir! Este documento explica como configurar o ambiente de desenvolvimento, abrir issues e enviar pull requests.

---

## Ambiente de desenvolvimento

**Requisitos:** Python 3.12+, Git

```bash
git clone https://github.com/dimmykarson/wig.git
cd wig

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt
```

Inicie o servidor:

```bash
uvicorn src.main:app --reload --port 5504
```

Acesse `http://localhost:5504`.

---

## Rodando os testes

```bash
python -m pytest
```

Com cobertura:

```bash
python -m pytest --cov=src --cov-report=term-missing
```

A cobertura mínima exigida é **80%**. O CI bloqueia PRs que ficarem abaixo desse limite.

---

## Convenção de commits

Este projeto segue o padrão **[Conventional Commits 1.0.0](https://www.conventionalcommits.org/)**.

Formato obrigatório:

```
<tipo>[escopo opcional]: <descrição imperativa, sem ponto final>

[corpo opcional]

[rodapé opcional]
```

Tipos aceitos: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `ci`, `build`, `chore`, `style`, `revert`

Exemplos:

```
feat(ws): adiciona timeout de inatividade no servidor
fix(ig): corrige estrutura do payload de delivery receipt
test(callback): cobre cenário de payload malformado
docs: atualiza quickstart com variável WS_INACTIVITY_TIMEOUT_S
```

Idioma: **português brasileiro** (termos técnicos permanecem em inglês).

---

## Abrindo um Pull Request

1. Crie um fork e uma branch descritiva: `feat/nome-da-feature` ou `fix/descricao-do-bug`
2. Siga o ciclo TDD: escreva o teste antes do código
3. Garanta que `python -m pytest` passa com zero falhas
4. Garanta que `ruff check src/ tests/` e `black --check src/ tests/` passam sem erros
5. Abra o PR com uma descrição clara do problema que resolve e da solução adotada

---

## Reportando bugs

Use o template de [bug report](.github/ISSUE_TEMPLATE/bug_report.md) ao abrir uma issue.

---

## Licença

Ao contribuir, você concorda que sua contribuição será licenciada sob a [MIT License](LICENSE).
