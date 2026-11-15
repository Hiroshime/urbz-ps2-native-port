# Preparação para o GitHub

O README da raiz apresenta o fork do Urbz. README-UPSTREAM.md e LICENSE preservam a documentação e os avisos do projeto de origem. O repositório de publicação é https://github.com/Hiroshime/urbz-ps2-native-port. O remote do upstream deve permanecer separado; a publicação contém somente as fontes auditadas.

## O que publicar

Publique somente fontes, scripts, documentação, licenças e relatórios textuais revisados. A configuração `.gitignore` exclui ISO, conteúdo extraído, fontes geradas do jogo, bibliotecas/ferramentas locais, executáveis, imagens, gravações e saves.

```bash
python3 scripts/prepare_urbz_github.py --check
python3 scripts/prepare_urbz_github.py --archive
```

O segundo comando cria `dist/source/urbz-ps2-source.tar.gz`, `SHA256SUMS` e `audit.json`. O arquivo contém o estado atual das fontes candidatas, incluindo alterações ainda não commitadas, sem `.git` e com proprietário de arquivos normalizado. Não exige a ISO para realizar a auditoria.

**Não publique `dist/Urbz-PS2-Windows`: esse pacote local contém a ISO e código recompilado do jogo.** O arquivo `dist/source/urbz-ps2-source.tar.gz` é a exportação separada destinada à revisão das fontes.

## Envio pelo Git

O remote `origin` existente aponta para o projeto upstream. Não envie as alterações diretamente para ele. Crie seu fork/repositório no GitHub e adicione um remote separado, usando a URL real escolhida:

```bash
git remote add publicacao URL_DO_SEU_REPOSITORIO
git status --short
git add -A
git diff --cached --stat
git diff --cached --check
python3 scripts/prepare_urbz_github.py --check
git commit -m "Prepare The Urbz PS2 native port prototype"
git push publicacao HEAD:main
```

Esses comandos são instruções para contribuições futuras; confirme o estado remoto antes de executá-los. Revise o diff completo antes do commit. A auditoria também verifica caminhos de objetos alcançáveis no histórico, mas a busca por padrões comuns de credenciais cobre os arquivos atuais, não todos os blobs históricos. Um resultado aprovado não substitui revisão de segredos ou de direitos sobre conteúdos adicionados posteriormente.

O checkout local atual é raso (`shallow`): a auditoria de histórico cobre somente os objetos disponíveis. Para um fork do upstream, mantenha a ancestralidade existente. Para um repositório novo e vazio, uma alternativa é extrair o arquivo de fontes em **outra pasta**, executar `git init` nessa cópia, revisar e criar seu primeiro commit. Isso evita depender do histórico incompleto e mantém LICENSE e README-UPSTREAM.md. Não reinicialize ou apague o `.git` deste workspace para fazer essa importação.

## Automação e limites

O workflow `source.yml` confere fontes e sintaxe sem dados do jogo. A compilação herdada `ci.yml` ficou disponível apenas por acionamento manual, pois seu ambiente precisa satisfazer a dependência OpenSSL 3.5.9+. Os workflows não foram executados remotamente nesta preparação. Não há publicação automática de executáveis ou releases.

Um clone limpo ainda precisa ser testado até o mesmo ponto de gameplay antes de anunciar uma instalação reproduzível para todos. Caches VU/EE, snapshots e código traduzido usados na validação local não acompanham as fontes.
