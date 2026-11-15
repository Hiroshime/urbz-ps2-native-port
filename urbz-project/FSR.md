FSR1 e saída Quad HD opcionais

O runtime oferece **FSR1 espacial**, com dois passes: EASU amplia a imagem considerando os contornos e RCAS aplica nitidez adaptativa. A implementação WGSL foi adaptada do [código MIT da AMD](https://github.com/GPUOpen-Effects/FidelityFX-FSR/tree/a21ffb8f6c13233ba336352bdff293894c706575), com operações FP32 e recíprocas de precisão completa. A licença e a revisão estão em `third_party/fsr1/`.

Para usar no Linux:

```bash
./Jogar-Linux.sh --graficos qhd --fullscreen
```

O perfil `qhd` solicita 2560×1440, usa resolução interna 2× e habilita FSR1. Preserva 4:3, com barras laterais numa tela 16:9. Para experimentar o filtro em outra saída, use `--graficos hd --fsr --window-size 1920x1080`. `--no-fsr` desliga o filtro naquela execução, inclusive com `--graficos qhd`. `--qhd` é um atalho apenas para o tamanho da janela; não seleciona automaticamente o perfil nem o filtro.

No pacote Windows:

```powershell
.\Jogar-Windows.cmd -Graphics qhd -Fullscreen
.\Jogar-Windows.cmd -Graphics qhd -Upscaler off
```

Para habilitar também a câmera e a interface 16:9 corrigidas, acrescente `--wide` no Linux ou `-Widescreen` no Windows. Consulte [WIDE-QHD.md](WIDE-QHD.md) para o escopo da validação.

Os atalhos de rede aceitam o perfil `qhd`. No Linux, também aceitam `--fsr` e `--window-size`; no Windows, `-Upscaler fsr1` e `-WindowSize 2560x1440`. FSR e tamanho da saída podem diferir entre jogadores; resolução interna, filtro 2D e proporção widescreen precisam coincidir.

O tamanho solicitado é independente da resolução interna. O compositor pode limitar uma janela maior que a área disponível. O log informa o tamanho inicial disponível, e o alvo do FSR acompanha redimensionamentos. Em tela cheia, a captura local confirmou 2560×1440 neste monitor. Outras telas dependem da resolução do desktop.

O filtro usa a apresentação direta WebGPU do runtime. Os testes disponíveis exercitaram Vulkan no Linux e no executável Windows via Wine. Direct3D 12 e Windows físico ainda precisam de validação. Quando o runtime usa a apresentação de contingência SDL, uma mensagem avisa que FSR está indisponível. Se a imagem interna já for maior que a área de saída em alguma dimensão, o runtime mantém o filtro anterior de redução, sem executar EASU/RCAS. Por isso `ultra` 4× em uma saída QHD não recebe automaticamente FSR.

A melhoria é de contornos e nitidez. **Não há geração de quadros, reconstrução temporal ou texturas HD.** Texturas, fontes e retratos continuam usando os dados originais. FSR1 não acrescenta o detalhe de um pacote de texturas novo e pode acentuar serrilhados em alguns elementos; a escolha permanece opcional. Quando ativo, EASU/RCAS substitui o filtro final `PS2_LOOK`; F2 volta a afetar a imagem quando FSR está desligado ou é dispensado na redução.

Validação local

`/usr/bin/python3 urbz-project/test_fsr_presentation.py` executa a mesma cena de dois jogadores com FSR desligado e ligado. Requer Pillow, NumPy, a ISO própria, o executável compilado, o snapshot privado `games/urbz-pal/validation/movement/frame17990.state` e um desktop de 2560×1440. `--widescreen` exercita a combinação com 16:9, e `--captures-only` dispensa a medição de desempenho. `--windows` usa o executável Windows por Wine; é preciso definir um `WINEPREFIX` adequado ao usuário que executa o teste.

O teste lê a imagem final apresentada pela GPU e verifica saída real QHD, barras 4:3 preservadas, imagens internas idênticas e checkpoints de gameplay idênticos. Compara também o desempenho sem capturas no intervalo medido, em execuções sequenciais sem limite, depois do aquecimento. Os arquivos ficam em `games/urbz-pal/validation/fsr/` e são excluídos da publicação.

A medição Linux com Ryzen 7 7800X3D e RTX 4070 SUPER ficou em 68,25 atualizações/s sem FSR e 68,53 com FSR, em interno 2× e saída QHD. São 400 atualizações PAL medidas depois do aquecimento; a diferença de uma passagem é pequena demais para concluir uma variação precisa de desempenho. O jogo continuou gerando uma imagem nova a cada duas atualizações. O limite normal permanece 50 Hz, aproximadamente 25 imagens novas/s. Esses resultados cobrem uma cena, sem certificar outras áreas ou GPUs.

A opção diagnóstica `PS2_PRESENT_CAPTURE=18080:caminho/imagem.ppm` captura o quadro final indicado, depois dos filtros. Ela desliga o envio assíncrono durante aquela execução para obter uma leitura determinística e não deve ser usada numa medição de desempenho normal. `--frames-dir` continua capturando a imagem interna antes do FSR.
