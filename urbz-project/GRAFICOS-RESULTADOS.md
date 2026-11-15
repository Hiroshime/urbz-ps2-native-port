Comparação real de resolução — 14 de novembro de 2026

Registro anterior à otimização. As capturas continuam representando a resolução e as texturas originais. Os resultados de desempenho do executável atualizado estão em [DESEMPENHO.md](DESEMPENHO.md).

Linux/Vulkan, Ryzen 7 7800X3D, NVIDIA RTX 4070 SUPER de 12 GB, driver 595.112.07. Primeira área em dois jogadores, partindo do mesmo snapshot no frame 17.990. Cada escala foi executada sozinha, duas vezes, numa janela de 960×720. A simulação usou um thread, recompilação durante a execução desativada e limite de velocidade desligado, aproximando o caminho usado em rede. O filtro de apresentação `sharp_edges` e o filtro 2D `1` foram mantidos constantes para comparar a resolução; o preset `original` usa apresentação `crisp`.

| Escala | Captura interna | Média de atualizações/s | Faixa dos dois ensaios | ms por atualização |
|---|---|---|---|---|
| 1× | 640×511 | 25,29 | 21,82–30,08 | 39,54 |
| 2× | 1280×1022 | 20,48 | 20,43–20,52 | 48,83 |
| 3× | 1920×1533 | 19,06 | 18,77–19,35 | 52,47 |
| 4× | 2560×2044 | 22,18 | 22,07–22,29 | 45,08 |

A referência de velocidade PAL é 50 atualizações simuladas por segundo. Neste trecho, o jogo gerou uma imagem nova a cada duas atualizações; as taxas da tabela não são FPS de imagens distintas. Nenhuma escala atingiu a velocidade original. A diferença entre os dois ensaios em 1× e a ordem não crescente das demais escalas impedem tratar esta amostra curta como uma classificação geral de desempenho.

Foram medidas 200 atualizações por ensaio, frames 18.101–18.300, depois de 110 atualizações de aquecimento. A abertura e a captura do frame 18.080 ficaram fora do intervalo medido. O log registrou 66.024 chamadas interpretadas de VU por intervalo e tempo médio de CPU entre aproximadamente 25 e 31 ms por atualização. Isso sugere que o custo da simulação também limita o desempenho; não é um perfil completo dos gargalos.

As capturas foram feitas antes dos filtros de apresentação, sem aprimoramento posterior. O PNG é uma conversão sem perdas do PPM original. Todas usam o mesmo snapshot inicial, comandos e número de frame; isso não significa que o estado interno entre escalas seja idêntico. Os testes de rede demonstraram que a resolução pode afetar leituras gráficas usadas pelo jogo. A comparação visual mostra melhora nos contornos 3D, com texturas e interface originais.

[Comparação interativa](../games/urbz-pal/validation/graphics/comparacao.html), [painel de imagens](../games/urbz-pal/validation/graphics/comparacao.png), [gráfico de desempenho](../games/urbz-pal/validation/graphics/desempenho.png) e [relatório bruto](../games/urbz-pal/validation/graphics/report.json).

O benchmark foi realizado no executável de hash `e59991a8fa6c892208e5199602c09c64633f393d611b9d8288e142eccb56a216`. Depois da medição, os executáveis foram reconstruídos para acrescentar a verificação de compatibilidade gráfica na conexão. A mudança não altera o renderer; os hashes atuais estão em `build-manifest.json`. Os testes de sincronização usam os executáveis reconstruídos e ficam em `last-graphics-validation.json`.

Esta amostra não certifica desempenho, fidelidade ou determinismo da campanha inteira. O modo offline com compilação de código durante a execução pode ter desempenho diferente. Windows real, outras GPUs e dois PCs físicos ainda precisam de validação.
