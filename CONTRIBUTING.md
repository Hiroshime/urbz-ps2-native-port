# Contribuir

O alvo deste fork é The Urbz PS2 PAL, SLES-52908. Consulte o README e o STATUS antes de alterar o comportamento do jogo.

## Relatar um problema

Informe revisão do código/build, sistema, CPU, GPU, driver, perfil gráfico e passos para reproduzir. Em rede, informe os dois sistemas, atraso configurado e se a conexão é local ou externa. Diferencie queda de desempenho, divergência de estado, erro visual e falha de save.

Não anexe ISO, executáveis do jogo, arquivos extraídos, código gerado, screenshots, saves, snapshots, gravações de entrada, chaves de partida ou endereços públicos pessoais. Logs devem ser revisados e reduzidos ao trecho necessário, removendo caminhos pessoais e dados de conexão. Não há necessidade de enviar dados do jogo para abrir uma issue.

## Propor uma alteração

1. Descreva o problema e a mudança de comportamento.
2. Preserve licença, créditos e compatibilidade com os cartões existentes.
3. Valide o trecho afetado. Mudanças em ponto flutuante, ordem de execução ou gráficos podem afetar determinismo e exigem comparação Linux/Windows e multiplayer.
4. Use fixtures próprias em pastas ignoradas. Não versione conteúdo derivado do jogo.
5. Execute `python3 scripts/prepare_urbz_github.py --check` e inclua os testes realizados e suas limitações na descrição do PR.

Os testes de gameplay locais não são reproduzíveis no CI sem a cópia do usuário e fixtures não distribuídas. Não apresente uma verificação de sintaxe como teste da campanha ou de desempenho.
