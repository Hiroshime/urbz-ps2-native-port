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

O remote `origin` do workspace original aponta para o upstream; seu histórico é diferente do snapshot publicado. Para novas contribuições, trabalhe num clone do repositório publicado em outra pasta. Não force um push do histórico upstream sobre `main`.

```bash
git clone https://github.com/Hiroshime/urbz-ps2-native-port.git urbz-publicacao
cd urbz-publicacao
# Faça as alterações de fontes neste clone.
git status --short
git add -A
git diff --cached --stat
git diff --cached --check
python3 scripts/prepare_urbz_github.py --check
git commit -m "Describe the source change"
git push origin main
```

Para importar alterações do workspace original, exporte o arquivo de fontes auditadas e extraia somente seu conteúdo nesse clone, preservando o `.git` do clone. Revise o diff completo antes do commit. Não copie as pastas de jogo, build, ferramentas ou pacote Windows. Não reinicialize ou apague o `.git` do workspace original.

A auditoria verifica caminhos de objetos alcançáveis no histórico, mas a busca por padrões comuns de credenciais cobre os arquivos atuais, não todos os blobs históricos. Um resultado aprovado não substitui revisão de segredos ou de direitos sobre conteúdos adicionados posteriormente. Num checkout raso, a auditoria de histórico cobre somente os objetos disponíveis.

## Automação e limites

O workflow `source.yml` confere fontes e sintaxe sem dados do jogo. A compilação herdada `ci.yml` ficou disponível apenas por acionamento manual, pois seu ambiente precisa satisfazer a dependência OpenSSL 3.5.9+. O workflow de fontes passou na publicação inicial; a compilação herdada não foi executada remotamente. Não há publicação automática de executáveis ou releases.

Um clone limpo ainda precisa ser testado até o mesmo ponto de gameplay antes de anunciar uma instalação reproduzível para todos. Caches VU/EE, snapshots e código traduzido usados na validação local não acompanham as fontes.
