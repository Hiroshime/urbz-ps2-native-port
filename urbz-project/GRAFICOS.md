Gráficos opcionais — The Urbz PS2 PAL

Os atalhos agora oferecem os mesmos perfis no Linux e no Windows. Nenhum perfil é ativado automaticamente: sem escolha, `padrao` preserva o ambiente e as opções existentes em `keys.ini`.

| Perfil | Resolução interna | Apresentação |
|---|---|---|
| `padrao` | Configuração existente | Configuração existente |
| `original` | 1× | Sem nitidez ou suavização adicionais |
| `hd` | 2× | Nitidez e suavização de contornos |
| `alto` | 3× | Nitidez e suavização de contornos |
| `ultra` | 4× | Nitidez e suavização de contornos |
| `qhd` | 2× | Saída 2560×1440 com FSR1 EASU/RCAS |

2× multiplica cada dimensão da renderização por dois; não significa saída 1080p. Na cena medida, as capturas internas foram 640×511, 1280×1022, 1920×1533 e 2560×2044. A apresentação padrão mantém a proporção original 4:3. O perfil `qhd` acrescenta [FSR1 e saída Quad HD](FSR.md). A correção opcional da câmera 16:9 está descrita em [WIDE-QHD.md](WIDE-QHD.md). Resoluções maiores melhoram os contornos 3D; as texturas e os elementos desenhados em bitmap continuam com o detalhe original.

No Linux, abra `./Configurar-Graficos.sh` na raiz do projeto e escolha o perfil. Para selecionar diretamente: `./Configurar-Graficos.sh hd`. A escolha fica em `games/urbz-pal/user/graphics.json`. Para uma única execução:

```bash
./Jogar-Linux.sh --graficos hd
./Hospedar-Internet.sh --graficos hd
./Entrar-Internet.sh IPv4-do-amigo --graficos hd
```

Os atalhos LAN também aceitam `--graficos`. A opção `--graphics` é equivalente. `./Configurar-Graficos.sh padrao` volta a usar a configuração existente. Os perfis explícitos fixam a resolução e o filtro 2D para aquela execução; o menu F1 informa que esses campos foram definidos pelo ambiente.

No pacote Windows, abra `Configurar-Graficos.cmd`. Também é possível usar `Configurar-Graficos.cmd -Profile hd`. A escolha fica em `user/graphics.json`. Para uma única execução, use `Jogar-Windows.cmd -Graphics hd`, `Hospedar-Internet.cmd -Graphics hd` ou `Entrar-Internet.cmd -Address IPv4-do-amigo -Graphics hd`. Os atalhos LAN aceitam a mesma opção. O launcher offline também aceita `-Fullscreen` e `-Frames 120`; opções avançadas do runtime podem ser usadas diretamente com `Urbz.exe`. Os atalhos PowerShell ainda precisam de teste em Windows real; o executável Windows foi exercitado via Wine/Vulkan.

A escolha explícita no comando tem prioridade sobre `URBZ_GRAFICOS`/`URBZ_GRAPHICS_PROFILE`, que têm prioridade sobre o arquivo salvo. O configurador escreve somente seu arquivo de preferências gráficas. ISO e cartões de memória não são modificados por ele.

Na rede, os dois jogadores precisam usar a mesma resolução interna e o mesmo filtro 2D. Escolher o mesmo perfil explícito nos dois PCs atende a essa condição. O teste de 1× contra 2× encontrou divergência no estado do jogo; por isso, a conexão agora rejeita essas diferenças antes de iniciar a simulação ou transferir o cartão compartilhado. Uma mensagem sobre `simulation settings (including internal resolution and 2D filtering)` indica essa incompatibilidade. Atualize os executáveis dos dois PCs juntos.

O filtro da imagem final (`PS2_LOOK`, alterável com F2), o FSR1 e o tamanho da saída podem variar por jogador. A proporção widescreen precisa coincidir. Ele não altera a resolução interna. O filtro 2D (`PS2_SHARP_2D`) participa da renderização e precisa coincidir quando a escala é maior que 1×. O menu F1 continua desativado em rede.

Comparação e desempenho medidos:

- [Comparação interativa offline](../games/urbz-pal/validation/graphics/comparacao.html): abra no navegador e arraste a divisão entre as imagens.
- [Quatro capturas lado a lado](../games/urbz-pal/validation/graphics/comparacao.png).
- [Resultados e limites da medição](GRAFICOS-RESULTADOS.md).

Para repetir, execute `./Comparar-Graficos.sh` na raiz. Ele usa o snapshot local da primeira área, gera capturas reais e mede cada escala em duas execuções sequenciais. A exportação usa Pillow e Matplotlib no Python do sistema; `URBZ_REPORT_PYTHON` permite indicar outro interpretador com essas dependências. O snapshot e a ISO não acompanham o código-fonte.

Estes perfis usam os recursos existentes do renderer: escala interna, filtro 2D e filtros de apresentação. FSR1 e saída Quad HD foram acrescentados como opções; consulte [FSR.md](FSR.md) para uso, evidências e limites. Geração de quadros e texturas HD continuam ausentes. Aumentar a resolução não garante velocidade integral. Depois da comparação gráfica inicial, o runtime foi [otimizado](DESEMPENHO.md): 1× e 2× passaram a superar a capacidade necessária para a velocidade PAL na cena medida, enquanto 4× permaneceu abaixo. Isso preserva o limite original de aproximadamente 25 imagens novas/s; não equivale a desbloquear 60 FPS.
