Otimização de desempenho — The Urbz PS2 PAL

Foram incorporados ao executável os programas vetoriais capturados durante os testes da cidade: o total registrado estaticamente passou de 81 para 92. No intervalo medido, as chamadas ao interpretador VU caíram de 145.551 para zero. O perfil de CPU anterior concentrou aproximadamente 65% das amostras nas três principais rotinas do interpretador VU.

No Linux, os headers SDL2 locais usavam uma configuração mínima e não expunham os campos de janela X11/Wayland. O host acabava usando a apresentação SDL com leitura da imagem para a CPU. A obtenção dos handles nativos agora funciona também com esses headers, permitindo apresentação direta pela GPU. A execução observada foi X11/Vulkan; o caminho Wayland ainda não foi exercitado. Headers SDL2 já configurados e o caminho Windows mantêm o tratamento existente.

| Resolução interna | Executável anterior | Com VU compilado | Com VU compilado e apresentação direta | Ganho total |
|---|---|---|---|---|
| 1× | 19,31 | 75,05 | 83,66 | 4,33× |
| 2× | 19,38 | 60,82 | 69,93 | 3,61× |
| 4× | 20,55 | 36,56 | 46,66 | 2,27× |

Os números são **atualizações simuladas por segundo com o limite desligado**, não FPS de imagens distintas. A versão PAL original desenha uma imagem nova a cada duas atualizações; 50 atualizações/s permitem sua velocidade original de aproximadamente 25 imagens/s. 1× e 2× ultrapassaram esse requisito na cena medida; 4× ficou abaixo. O launcher normal mantém o limite de velocidade, portanto a folga não deve acelerar o jogo.

[Gráfico da comparação](../games/urbz-pal/validation/performance/desempenho-comparado.png).

Medição: Ryzen 7 7800X3D, RTX 4070 SUPER, Linux/Vulkan; primeira área com dois jogadores. Um thread de simulação, compilação durante a execução desligada, janela 960×720 e apresentação imediata sem limite. Duas execuções por escala e variante, com ordem alternada. Foram medidas 400 atualizações após 110 de aquecimento em cada execução. Os comandos e checkpoints de gameplay coincidiram com o executável anterior em todos os ensaios da mesma escala. Não houve mudança de resolução, texturas ou efeitos para produzir o ganho.

[Relatório bruto](../games/urbz-pal/validation/performance/report.json). Para repetir, preserve o executável anterior em `build/performance-baseline/ps2run` e execute `python3 urbz-project/benchmark_performance.py` na raiz. Os relatórios do benchmark gráfico inicial continuam sendo registros da versão anterior; consulte este arquivo para a medição após otimização.

60 imagens novas por segundo são uma mudança separada do motor. A investigação está em [FPS-INVESTIGACAO.md](FPS-INVESTIGACAO.md). Os experimentos usam somente pastas de validação, sem cartões pessoais, e não são selecionados pelos launchers. O objetivo de 60 FPS estáveis ainda depende de remover o limite original, corrigir o relógio do motor e validar física, animações, áudio, menus e sincronização.

O experimento de uma imagem nova por vblank a 60 Hz produziu 600 imagens em 600 atualizações virtuais. Com o relógio PAL intacto, o motor acumulou 12,02 s durante 10 s virtuais, confirmando aceleração de cerca de 20%. Com quantum de 1/60 s e região ajustada, acumulou 10,0167 s em 10 s virtuais. Isso valida somente o acumulador de tempo nesse trecho, sem certificar física, animações ou minijogos.

No renderer sequencial, o candidato corrigido ficou em aproximadamente 45,5 imagens novas/s em 1×. Variar tiles de 4/8/16 pixels e a thread de submissão manteve as capturas e checkpoints iguais, mas não atingiu 60 FPS.

A renderização paralela chegou a aproximadamente 103 imagens novas/s quando usava o cache antigo de leituras gráficas. Esse resultado foi rejeitado: duas execuções iguais produziram checkpoints diferentes. O cache podia reutilizar dados de um framebuffer anterior, conforme o avanço da thread da GPU. Agora as sessões de rede usam leituras do buffer atual; `PS2_GS_SYNC_READBACK=1` permite verificar o mesmo caminho offline. Na repetição com os executáveis finais, duas execuções ficaram em 52,09 e 52,04 imagens novas/s, com checkpoints idênticos entre elas e ao modo sequencial. Desligar a helper de tiles e usar tiles de 16 pixels não melhorou o resultado; a tentativa sem instrumentação ficou em 51,23 imagens/s.

Os launchers offline desativam a thread VU separada e pedem leituras exatas. Em rede, CPU e VU ficam na mesma thread de simulação, com a renderização da janela em paralelo e leituras atuais obrigatórias. O modo headless continua sequencial. A compilação durante a execução continua desligada em rede. O protocolo e os cartões mantêm seu formato; os dois jogadores precisam atualizar os executáveis juntos devido à identidade do código.

Para repetir os experimentos isolados: `python3 urbz-project/probe_high_fps.py`, `--tuning` e `--threading`. Eles requerem o snapshot PAL local. A alternativa com VU em outra thread foi descartada nesta medição: avançou os vblanks, mas produziu apenas duas imagens, o que não serve como evidência de desempenho. Os experimentos de 60 Hz não acompanham os launchers como modo de jogo suportado. A meta de 60 FPS estáveis ainda não foi entregue.

A regressão dos executáveis finais aprovou 14 casos gráficos de rede, incluindo diferenças de configuração rejeitadas e filtros finais independentes. A abertura com janelas Linux/Windows via Wine manteve 40 comparações iguais em 1.200 frames. Uma gravação real pelo menu, também com renderização paralela e TLS, manteve 43 comparações iguais em 1.300 frames, com 6.180 escritas de páginas em cada cartão e cartões finais idênticos. O relatório completo está em `last-performance-validation.json`. Os testes usam TCP loopback; dois PCs físicos e Windows real ainda precisam de validação.
