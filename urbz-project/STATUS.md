The Urbz PS2 PAL — estado atual

O projeto executa a revisão europeia SLES-52908 no Linux e produz um executável Windows, exercitado via Wine/Vulkan. A primeira área foi jogada em dois jogadores, com tela dividida e comandos independentes. A campanha inteira, dois PCs físicos e uma conexão real entre redes externas ainda não foram certificados.

O fluxo de build traduz o código EE do jogo para C++ e usa o runtime PS2 da base ps2-native-recomp. Não é um utilitário ARM64 do Hookshot. A toolchain Clang do Hookshot foi reutilizada localmente; o tradutor e o runtime deste projeto são de PS2. Ambos os builds locais exigem AVX2 e desabilitam a fusão automática de multiplicação com soma.

O código-fonte está publicado em https://github.com/Hiroshime/urbz-ps2-native-port. A publicação exclui ISO, arquivos extraídos, C++ derivado do jogo, executáveis, cartões, snapshots e capturas. O usuário precisa fornecer sua própria cópia legitimamente adquirida da revisão compatível. O pacote em `dist/Urbz-PS2-Windows` é privado e pode conter a ISO local; ele não deve ser enviado ao repositório ou a Releases.

Uso e saves

Use `./Jogar-Linux.sh` ou `Jogar-Windows.cmd` para jogar offline. Os controles usam SDL2. A regressão anterior passou com 62 verificações de controles virtuais e 85 de arquivos de saves/snapshots. Controles físicos ainda precisam de teste nas máquinas dos jogadores.

O save nativo é o cartão usado pelo menu Save/Load do jogo. A gravação e a retomada dos dois personagens foram validadas em trechos específicos. F5/F8 gerenciam snapshots offline; eles são separados do cartão. Não há certificação de todas as missões ou de sessões longas.

Rede e Internet

O netplay lockstep TCP permite um jogador por PC e conserva a tela dividida original em ambas as máquinas. A sessão valida identidade dos fontes/código traduzido, ISO, ELF, idioma, temporização, escala interna, filtro 2D e widescreen. O anfitrião fornece o relógio e o cartão compartilhado; o cliente recebe uma cópia antes do boot e preserva seu cartão anterior em backup. A ISO não é transferida.

Os atalhos Hospedar-Internet/Entrar-Internet usam IPv4 público e TLS 1.2 DHE-PSK/AES-128-GCM com chave aleatória da partida. O anfitrião precisa encaminhar TCP 27888 e ter entrada acessível no IPv4 público. VPN ou servidor em nuvem não são necessários nesse método. Não há travessia automática de NAT, relay, lobby, rollback, reconexão ou lista pública de salas. Os atalhos LAN sem TLS destinam-se a uma rede privada confiável. Consulte LAN.md e INTERNET.md.

Foram validados protocolo, atrasos simulados, fragmentação, detecção de desync, recusas de configurações incompatíveis, transferência e backup de cartões, gameplay e saves entre Linux/Linux e Linux/Windows via Wine. A retomada de uma partida a partir do cartão passou em 17.000 frames e 566 comparações de estado. A sobrescrita real pelo menu passou em 1.300 frames, 43 comparações iguais e cartões finais idênticos; esse trecho foi repetido com janelas/TLS após a integração gráfica atual.

A comparação periódica inclui RAM EE/IOP, registradores e parte de VU0. Não abrange todo o estado VU1, GS e dispositivos. A compilação adicional em tempo de execução fica desativada em rede; novas áreas podem exigir descoberta offline e reconstrução dos dois builds. O menu F1 e snapshots ficam desativados na sessão de rede. Use Save no próprio jogo.

Gráficos e fluidez

Os perfis opcionais `original`, `hd`, `alto` e `ultra` usam interno 1×, 2×, 3× e 4×. `padrao` mantém as preferências existentes. O novo `qhd` usa interno 2×, solicita saída 2560×1440 e aplica FSR1 EASU/RCAS. As texturas continuam originais; não há geração de quadros ou pacote de texturas HD. Consulte GRAFICOS.md e FSR.md.

O widescreen opcional corrige a câmera 3D para 16:9 e centraliza a interface Apt com sua proporção original. A primeira área em dois jogadores mostrou maior campo de visão, personagens sem alongamento e retratos/textos do HUD proporcionais. Outras câmeras, telas, vídeos e indicadores ligados a objetos ainda precisam de validação. 4:3 permanece o padrão. Consulte WIDE-QHD.md.

FSR e tamanho da saída podem diferir entre jogadores. Resolução interna, filtro 2D e widescreen precisam coincidir. Seis novos testes em loopback passaram: FSR distinto, widescreen igual e rejeição de widescreen diferente, em Linux/Linux e Linux/Windows via Wine. Os 14 casos gráficos anteriores permanecem documentados com seus builds históricos.

O alvo de fluidez é o original PAL: aproximadamente 25 imagens novas por segundo em vídeo de 50 Hz. O benchmark anterior ao trabalho de desempenho está preservado em GRAFICOS-RESULTADOS.md; ele não representa a velocidade atual. Depois do AOT de 92 programas VU e da apresentação direta por GPU, a cena em interno 2× passou a superar a capacidade necessária para PAL. O teste sequencial QHD mediu 68,25 atualizações/s sem FSR e 68,53 com FSR no Linux, com os mesmos checkpoints. A medição usa uma cena e não certifica outras áreas ou GPUs.

O modo com janela usa renderização paralela, CPU/VU na mesma thread de simulação e leituras exatas do framebuffer. Headless permanece sequencial. Os experimentos de desbloqueio de 60 Hz ficaram fora dos launchers; não há modo de 60 FPS suportado. Consulte DESEMPENHO.md e FPS-INVESTIGACAO.md.

Relatórios

`build-manifest.json` identifica os executáveis atuais. `last-fsr-wide-validation.json` registra a integração gráfica recente; os demais arquivos `last-*-validation.json` e documentos de desempenho conservam os resultados e hashes de suas respectivas etapas. ISO, snapshots, capturas e logs brutos permanecem nas pastas locais ignoradas. O workflow GitHub verifica fontes, auditoria e sintaxe; não executa o jogo sem a ISO e fixtures privadas.
