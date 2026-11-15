O protótipo agora sincroniza os dois controles pela rede usando TCP/IPv4. Cada PC executa o jogo inteiro, espera pelos comandos necessários e compara partes do estado da simulação a cada 30 frames. As primeiras sessões foram validadas em loopback, incluindo Linux com o executável Windows via Wine. Ainda falta testar dois PCs físicos e uma partida longa.

Use exatamente a mesma versão do protótipo e sua ISO PAL SLES-52908 em ambos os PCs. A conexão verifica o código do runtime e do jogo, a ISO inteira, a configuração, o snapshot inicial e o cartão, quando houver. Essa leitura da ISO pode levar algum tempo antes de abrir a janela. Os dados do jogo não são enviados pela conexão. O cartão de memória compartilhado do anfitrião é enviado ao cliente antes de iniciar.

No Linux, execute na pasta do projeto:

```bash
# PC do jogador 1
./Hospedar-LAN.sh
# PC do jogador 2: substitua pelo IPv4 local do primeiro PC
./Entrar-LAN.sh 192.168.1.20
```

No Windows, abra `Hospedar-LAN.cmd` no primeiro PC e `Entrar-LAN.cmd` no segundo. O segundo atalho pede o IPv4 do anfitrião. Ambos estão em `dist/Urbz-PS2-Windows`, junto ao jogo. Os scripts usam o Windows PowerShell. Windows real, incluindo esses atalhos, ainda precisa de validação.

A porta padrão é TCP 27888; o anfitrião escuta nas interfaces IPv4. No Windows, permita o aplicativo na rede privada se o firewall solicitar. Comece com os dois PCs na mesma rede local. O tempo máximo de espera dos atalhos é cinco minutos. Após conectar, o anfitrião escolhe **2 Player** no menu do jogo. Ambos verão a tela dividida original. Cada PC usa seu primeiro controle físico ou teclado: o comando local é encaminhado à porta 1 no anfitrião e à porta 2 no cliente. Não é necessário conectar um segundo controle ao PC do cliente.

No teclado, WASD move o analógico esquerdo; setas controlam o direcional; Enter/Espaço corresponde a X; E a círculo; botões esquerdo/direito do mouse a quadrado/triângulo; Esc a Start; Tab a Select. F1 mostra e permite configurar o mapa em uma execução offline. Durante LAN, F1 e os atalhos de salvar/carregar snapshots ficam desativados. O pause do próprio jogo, via Start, continua sendo um comando sincronizado.

O atraso inicial é de 3 frames, aproximadamente 60 ms em PAL, além de eventuais esperas pela rede ou pelo outro PC. Para alterá-lo, use o mesmo valor dos dois lados:

```bash
URBZ_NET_DELAY=5 ./Hospedar-LAN.sh 27888
URBZ_NET_DELAY=5 ./Entrar-LAN.sh 192.168.1.20 27888
```

No Windows, os atalhos aceitam `-Port 27888 -Delay 5`; `Entrar-LAN.cmd` também aceita `-Address 192.168.1.20`. Portas diferentes ou atraso diferente impedem a sessão. O protocolo aceita atrasos de 0 a 12 frames.

Os atalhos criam um cartão vazio já formatado no primeiro uso e usam um cartão separado por papel: `user/lan-host/card.ps2` no anfitrião e `user/lan-join/card.ps2` no cliente (no Linux, sob `games/urbz-pal/`). O cartão do anfitrião é a referência e é copiado automaticamente ao cliente ao conectar. Se o cartão anterior do cliente for diferente, uma cópia fica em `card.ps2.before-net.ps2` antes da substituição. Falha de backup ou instalação impede o início. Os saves offline em `user/card.ps2` permanecem separados. Para salvar, use Start → Save → MEMORY CARD slot 1 no próprio jogo e aguarde a conclusão. Ao sobrescrever, selecione explicitamente Yes; o padrão é No. Retome pelo Load Game na próxima sessão; mantenha o mesmo anfitrião. As gravações de comandos e os logs de LAN ficam em `user/lan-host` e `user/lan-join` (no Linux, sob `games/urbz-pal/`). O programa informa no log o motivo de uma incompatibilidade, desconexão ou `DESYNC`, e interrompe a sessão. Fechar a janela encerra sua participação; não há reconexão.

O cartão contém o progresso salvo pelo jogo, e não um snapshot de cada frame. F5/F8 continuam desativados na rede. A sessão confere o cartão completo antes de começar e os cartões em memória ao terminar normalmente. Em desconexões, cada PC conserva o que conseguiu gravar; na próxima conexão, prevalece o anfitrião. Cópias antigas também podem ficar em `card.backups` pelo mecanismo de backups do runtime.

Para iniciar com outro cartão no Linux, passe `--memcard caminho.ps2`, sempre usando uma cópia dedicada à campanha compartilhada. No Windows, as opções avançadas podem ser passadas diretamente a `Urbz.exe`. O CLI `--net-sync-card` exige cartão e boot inicial, sem `--load-state`. Os testes de snapshots continuam possíveis pelo CLI sem essa opção, com arquivos iniciais idênticos preparados manualmente. Não há sincronização de snapshots ou mesclagem de campanhas.

Para jogar pela Internet por IPv4 público, consulte [INTERNET.md](INTERNET.md). Os atalhos Hospedar-Internet/Entrar-Internet agora pedem uma chave de partida e usam TLS, sem depender do Tailscale. O anfitrião precisa encaminhar a porta TCP no roteador e ter entrada disponível no IPv4 público. Os atalhos LAN continuam destinados a uma rede privada e não ativam TLS por padrão; use os atalhos de Internet ao publicar a porta.

Para repetir a validação local:

```bash
./Validar-LAN.sh
# Inclui Windows via Wine e janelas com controles virtuais:
./Validar-LAN.sh --windows --windowed
./Validar-Saves-Rede.sh
./Validar-Saves-Rede.sh --windows
```

O segundo comando requer Wine, um display gráfico disponível e os snapshots locais de exploração. Os relatórios ficam em `games/urbz-pal/validation/lan-protocol/report.json` e `lan-game/report.json`. O teste de protocolo não precisa da ISO e verifica roteamento dos controles, diferentes atrasos, fragmentação de pacotes, desync, incompatibilidades, desconexão e timeout. Os testes com o jogo usam sua ISO e comparam as gravações dos dois lados. Os arquivos da campanha usados nos testes ficam fora do código-fonte.

A comparação de estado inclui RAM do EE e IOP, registradores de CPU e parte do estado VU0. Não abrange todo o estado de VU1, GS e dispositivos, portanto não certifica determinismo de toda a campanha. A compilação de código adicional durante a execução fica desativada em LAN; se uma nova área exigir código ainda ausente, será necessário reconstruir os dois builds com essa descoberta. O modo offline mantém a compilação durante a execução.

Esta versão usa atraso de comandos e espera pelo parceiro. O modo LAN sem --net-secure não implementa autenticação ou criptografia; os atalhos de Internet agora fornecem autenticação e criptografia TLS com chave aleatória de partida. O uso real entre duas casas ainda precisa de teste, assim como sessões longas e transições. O protocolo atual é a versão 3; ambos os jogadores precisam atualizar os executáveis.
