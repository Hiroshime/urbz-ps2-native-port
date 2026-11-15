Protótipo de The Urbz: Sims in the City para PS2 PAL, SLES-52908, com dois jogadores locais e sincronização experimental por LAN.

Abra [Jogar-Linux.sh](../Jogar-Linux.sh) para jogar offline no Linux. A ISO original permanece em Downloads; o projeto usa um link em games/urbz-pal/disc.iso. O idioma inicial é inglês. F1 mostra controles e opções; F5/F8 salvam e carregam snapshots. Os arquivos pessoais ficam em games/urbz-pal/user. Dois controles físicos permitem usar o modo local de dois jogadores.

Os [gráficos opcionais](GRAFICOS.md) oferecem perfis `original` (1×), `hd` (2×), `alto` (3×) e `ultra` (4×). Use `./Configurar-Graficos.sh` ou `Configurar-Graficos.cmd` no pacote Windows. Sem escolha, `padrao` preserva as opções existentes. Para uma abertura, use `./Jogar-Linux.sh --graficos hd` ou `Jogar-Windows.cmd -Graphics hd`. Os atalhos de rede aceitam o mesmo perfil; resolução e filtro 2D precisam coincidir nos dois PCs. Há uma [comparação real interativa](../games/urbz-pal/validation/graphics/comparacao.html), [medições gráficas iniciais](GRAFICOS-RESULTADOS.md) e [resultados após otimização](DESEMPENHO.md). No executável atualizado, 1× e 2× superaram a capacidade necessária para a velocidade PAL na cena medida; isso mantém o limite original de aproximadamente 25 imagens/s.

Para rede, use [Hospedar-LAN.sh](../Hospedar-LAN.sh) no PC do jogador 1 e `./Entrar-LAN.sh IPv4-do-host` no PC do jogador 2. Escolha 2 Player dentro do jogo. Cada pessoa usa o primeiro controle ou teclado do próprio PC; ambos veem a tela dividida original. Leia [LAN.md](LAN.md) para conexão, controles, atraso, saves e limitações. Os atalhos de LAN sincronizam o cartão do anfitrião e mantêm snapshots desativados durante a sessão. Salve pelo menu Save do próprio jogo. Para outra casa, veja [INTERNET.md](INTERNET.md): os atalhos Hospedar-Internet/Entrar-Internet usam IP público e chave de partida por TLS. O anfitrião precisa encaminhar a porta TCP 27888 e verificar a disponibilidade de IPv4 público.

O executável Windows fica em build/wine-urbz-pal/ps2run.exe. Empacotar-Windows.sh monta dist/Urbz-PS2-Windows com Jogar-Windows.cmd, atalhos de LAN e Internet, a ISO local, SDL2, DXC e o compilador usado no modo offline. O pacote contém arquivos da cópia local do jogo e não foi publicado. O executável foi testado via Wine; Windows real, incluindo os atalhos PowerShell, ainda precisa de validação.

Comandos a partir da raiz:

```bash
./Jogar-Linux.sh
./Hospedar-LAN.sh
./Entrar-LAN.sh 192.168.1.20
./Construir-Linux.sh
./Construir-Windows.sh
./Validar-LAN.sh --windows --windowed
./Validar-Multiplayer.sh --windows --gameplay
./Validar-Saves-Rede.sh --windows
./Validar-IP-Publico.sh --windows --case wan
./Empacotar-Windows.sh
```

A validação de rede usa TCP real entre processos locais e um proxy com atraso e pacotes fragmentados. Confere roteamento dos controles, incompatibilidades, desconexão, timeout e detecção de desync. Seis cenários com o jogo passaram, incluindo Linux/Windows via Wine e duas janelas com controles virtuais. Os relatórios ficam em games/urbz-pal/validation/lan-protocol/report.json e lan-game/report.json. Dois PCs físicos e Internet ainda não foram testados.

A regressão offline grava 5.000 frames e compara 333 checkpoints no Linux e no executável Windows via Wine. Uma alteração de comando confirma a detecção de divergência. A opção --gameplay inclui a primeira área, dos frames 17.990 a 18.500, com 34 checkpoints e comandos diferentes nos dois controles. Os oito testes passaram, incluindo controles e arquivos de save. O relatório fica em games/urbz-pal/validation/multiplayer-baseline/report.json. Os snapshots e gravações permanecem em games/ e não fazem parte do código-fonte.

Os checkpoints offline abrangem registradores e fatias da RAM do EE. A comparação LAN acrescenta toda a RAM do EE/IOP e campos de CPU/VU0, mas ainda não cobre integralmente VU1, GS e dispositivos. Os trechos iguais não certificam determinismo ou estabilidade da campanha completa. Os resultados e pendências estão em [STATUS.md](STATUS.md).

A base é ps2-native-recomp na revisão indicada em game.json, com licença e créditos preservados. A toolchain Linux reutiliza Clang extraído localmente do Hookshot; o tradutor usado é específico de PS2. Os builds exigem AVX2 e desabilitam a fusão automática de multiplicação com soma. O Linux foi construído no Nobara atual; outras distribuições ainda precisam de validação. A SDL2 real 2.32.10 passou nas 62 verificações de controles e substituiu a SDL2-compat do sistema, que falhou no teste de parada da vibração.

As entradas adicionais descobertas no boot estão em entries.txt. ISO, código gerado, snapshots, executáveis e capturas ficam fora do controle de versão. Os testes usam suas próprias pastas em validation e não alteram os saves em user.

O transporte de Internet requer OpenSSL 3.5.9 ou mais recente na compilação Linux. O Windows incorpora OpenSSL estaticamente; Construir-Windows.sh baixa a fonte oficial 3.5.9 com SHA-256 fixado e faz a compilação cruzada. A licença está em licenses/OpenSSL-3.5.9.txt. Os dois executáveis precisam ser atualizados para o protocolo 3.
