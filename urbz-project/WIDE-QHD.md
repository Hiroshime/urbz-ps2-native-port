Widescreen e saída Quad HD — integração opcional

`--window-size 2560x1440` solicita saída Quad HD. Também é possível definir `PS2_WINDOW_SIZE=2560x1440`; a opção explícita no comando tem prioridade. Dimensões inválidas são rejeitadas, com limite de 320×240 a 7680×4320. O tamanho de saída é independente da resolução interna (`PS2_SCALE`). O compositor pode limitar o tamanho real da janela; o log registra o tamanho solicitado e os pixels disponíveis. A captura em tela cheia confirmou 2560×1440 no monitor local.

Para combinar Quad HD, FSR1 e widescreen no Linux:

```bash
./Jogar-Linux.sh --graficos qhd --wide --fullscreen
```

No pacote Windows:

```powershell
.\Jogar-Windows.cmd -Graphics qhd -Widescreen -Fullscreen
```

`--wide` é o atalho do launcher Linux para `--widescreen`. Também é possível usar `--graficos hd --widescreen --window-size 2560x1440`, sem habilitar FSR. Sem a opção widescreen, a apresentação preserva 4:3 com barras laterais. O perfil `qhd` sozinho mantém essa proporção original. Tudo permanece opcional; os gráficos originais continuam disponíveis com `--graficos original`.

Em 16:9, a integração corrige a projeção 3D para mostrar mais cenário nas laterais e aplica uma transformação separada à interface Apt/Flash. Na cena de dois jogadores testada, os personagens, retratos e textos mantêm a proporção, e os dois HUDs ficam dentro de suas respectivas metades. A interface ocupa uma região central 4:3 dentro da saída 16:9; seus elementos não são redesenhados para preencher as bordas. Isso não acrescenta detalhe às texturas originais.

A validação cobre a primeira área em tela dividida e uma comparação do menu inicial. Nesse menu, o conteúdo Apt permanece centralizado em 4:3 dentro da tela maior, com margens laterais. Outras câmeras, telas de personalização, vídeos, indicadores sobre objetos, transições e sessões longas ainda precisam ser exercitados. O modo permanece experimental, sem certificação da campanha inteira.

Como a integração funciona

O getter de aspecto da revisão SLES-52908 fica em `0x0039B3F0`. A constante original `0x3FAAAAAB` representa 4:3; `0x3FE38E2A` representa 16:9. Essa parte segue a correção de câmera atribuída a **Arapapa** no [patch público dessa revisão](https://github.com/PeterDelta/PCSX2/blob/main/patches/SLES-52908_25C3948E.pnach).

A correção da câmera sozinha deixava o HUD alongado. O callback Apt em `0x00104998` copia a matriz afim 2D para `0x004C13C0`. A integração opcional aplica `x' = 0,75x + 80` às componentes horizontais dessa matriz, no espaço lógico de 640 pixels. Quando a apresentação amplia para 16:9, o HUD volta à proporção original e permanece centralizado. A transformação é restrita à interface Apt; não modifica genericamente os desenhos do GS. As operações usam a aritmética de ponto flutuante do EE e preservam os flags FPU do código original para manter o comportamento entre builds.

Como o jogo foi traduzido para C++, escrever somente os opcodes de um patch na RAM não modifica as instruções compiladas. `apply_game_features.py` verifica o SHA-256 do ELF, os opcodes originais e o formato do trecho traduzido antes de acrescentar as duas escolhas condicionais. Uma tradução inesperada interrompe a aplicação. A ISO e o ELF original não são modificados; o C++ derivado permanece na pasta local ignorada `generated/`.

`Construir-Linux.sh` e `Construir-Windows.sh` aplicam a integração durante o build. O script é idempotente; `python3 urbz-project/apply_game_features.py --check` verifica se os dois hooks estão presentes. Ambos dependem de `g_options.widescreen`, que fica desabilitado por padrão. A identidade de rede inclui o código traduzido e essa configuração: os dois parceiros devem atualizar o build e usar a mesma proporção. O tamanho da saída e o FSR podem diferir entre jogadores.

Evidências locais

`python3 urbz-project/test_wide_qhd.py` captura o mesmo snapshot e frame em 4:3 e 16:9, com saída QHD solicitada. `--scene title` repete a comparação no menu inicial. Os relatórios ficam em `games/urbz-pal/validation/wide-qhd/`.

`/usr/bin/python3 urbz-project/analyze_wide_qhd.py` usa Pillow e Matplotlib para medir marcos específicos dos dois personagens e os dois relógios do HUD. Na cena testada, a relação largura/altura dos personagens em widescreen ficou em 97,8% e 96,7% do original; os textos dos relógios conservaram a proporção original. Um simples alongamento horizontal produziria cerca de 133,3%. O relatório `geometry.json` registra as caixas e os limites de cada medição. A inspeção visual confirmou maior campo de visão e retratos sem o alongamento da versão apenas com a câmera corrigida.

A combinação FSR1/16:9 também foi capturada em saída real de 2560×1440 nos executáveis Linux e Windows via Wine. As imagens finais coincidiram entre os dois builds. Os testes de rede verificaram estados iguais com widescreen nos dois parceiros e rejeitaram proporções diferentes antes da sessão. Os artefatos com imagens do jogo ficam locais, fora da publicação do código. Consulte [FSR.md](FSR.md) para o teste de apresentação final.

A variante MIPS R5900 do ELF não é suportada pelos provedores REA disponíveis neste ambiente, conforme a investigação anterior em FPS-INVESTIGACAO.md. Os hooks foram derivados do código traduzido, dos opcodes originais verificados e, para a câmera, do patch comunitário; não são uma decompilação REA validada para este alvo.
