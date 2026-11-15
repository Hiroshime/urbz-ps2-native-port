A conexão de Internet agora é direta por **IPv4 público**, sem Tailscale, VPN, conta externa ou servidor na cloud. O anfitrião recebe a conexão TCP do amigo. Cada PC continua executando o modo original de dois jogadores e ambos veem a tela dividida.

No PC do anfitrião, abra `Hospedar-Internet.sh` no Linux ou `Hospedar-Internet.cmd` no Windows. O atalho consulta o IPv4 público e mostra uma **chave aleatória da partida**, com 32 caracteres. Envie o IPv4 e a chave ao amigo por um canal privado. A consulta do IP usa HTTPS em api.ipify.org e não envia a chave. Se essa consulta falhar, o jogo ainda pode hospedar; consulte o IP no roteador ou por outro serviço.

O amigo abre `Entrar-Internet.sh SEU_IPV4_PUBLICO` no Linux, ou `Entrar-Internet.cmd` no Windows, informa o IPv4 público e copia a chave completa quando solicitado. Os dois PCs precisam da mesma versão atualizada do protótipo e da mesma revisão PAL da ISO. A porta padrão é **TCP 27888**. Os dois lados usam 6 frames de atraso, aproximadamente 120 ms em PAL, mais eventuais esperas pela rede e pelo processamento.

No Linux, a partir da pasta do projeto:

```bash
# Anfitrião: gera e exibe a chave
./Hospedar-Internet.sh
# Amigo: informe o IPv4 público do anfitrião; a chave é solicitada separadamente
./Entrar-Internet.sh 203.0.113.20
```

O endereço acima é apenas um exemplo. Para mudar a porta, use `./Hospedar-Internet.sh 27889` e `./Entrar-Internet.sh IP 27889`. No Windows os atalhos aceitam `-Port 27889`; o cliente também aceita `-Address IP`. O amigo deve usar a porta externa configurada no roteador, e ambos precisam do mesmo atraso. Os exemplos usam o mesmo número de porta interno e externo. `URBZ_NET_DELAY=8` no Linux ou `-Delay 8` no Windows altera o atraso para ambos. A chave pode ser fornecida pela variável de ambiente `URBZ_NET_KEY` em uma automação; não a coloque nos argumentos do executável ou em capturas de tela públicas.

Para receber conexões externas, configure no roteador do anfitrião um encaminhamento de porta (NAT / Port Forwarding / Virtual Server):

| Campo | Valor |
|---|---|
| Protocolo | TCP |
| Porta externa | 27888 |
| IP interno de destino | IPv4 local do PC anfitrião, mostrado pelo atalho Linux ou pela configuração de rede do sistema |
| Porta interna | 27888 |

Reserve esse IPv4 local no DHCP do roteador para que a regra continue apontando para o mesmo PC. O IP local, como 192.168.x.x ou 10.x.x.x, é o destino da regra; o amigo em outra casa deve usar o IPv4 público. Mantenha o jogo hospedando durante o teste. A conferência da ISO acontece antes de abrir a porta e pode levar alguns segundos; aguarde a mensagem de espera pela conexão no console. No Windows, permita `Urbz.exe` no firewall do anfitrião para o perfil de rede em uso. No Nobara, verifique a zona ativa do firewalld e permita somente o TCP necessário; não é preciso desligar o firewall. Nesta máquina, a configuração existente já permite a porta 27888, sem alteração de regras por este trabalho.

Confira o **IPv4 WAN/Internet** mostrado pelo roteador e compare com o IP público observado. Um IP privado na WAN ou um endereço entre 100.64.0.0 e 100.127.255.255 indica outro NAT à frente; pode ser um segundo roteador ou NAT do provedor. Nesse caso, uma regra apenas no roteador da casa pode não bastar. Consulte o provedor sobre IPv4 público com entrada liberada ou escolha como anfitrião o amigo que dispõe dele. A faixa compartilhada de CGNAT está descrita no [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598.html). Apenas o IP privado da placa de rede do PC não permite concluir se existe CGNAT.

Uma conexão TCP a partir de outra rede é a verificação necessária. Por exemplo, no PC Windows do amigo, com o anfitrião aberto:

```powershell
Test-NetConnection IP_PUBLICO_DO_ANFITRIAO -Port 27888
```

`TcpTestSucceeded: True` comprova a entrada TCP, mas o jogo ainda exige a chave e arquivos compatíveis. Esse teste de porta não conhece a chave, portanto pode produzir no anfitrião uma mensagem de tentativa não autenticada rejeitada; ele continua esperando pelo amigo. Um teste usando o IP público de dentro da mesma casa pode depender de NAT loopback do roteador e não substitui a verificação externa.

A conexão dos atalhos de Internet usa **TLS 1.2 com DHE-PSK e AES-128-GCM**, pelo OpenSSL 3.5.9. A chave não é enviada em texto puro. A autenticação termina antes de transmitir o cartão ou iniciar a sessão de jogo. Uma chave errada, um cliente sem TLS ou dados criptografados alterados são rejeitados; o anfitrião continua aguardando uma conexão válida dentro do prazo de espera. Não há certificados para instalar, autenticação por conta, lobby, lista de salas, relay ou travessia automática de NAT. O protocolo atual é a versão 3; atualize os dois executáveis.

O **save de referência continua sendo o do anfitrião**. No Linux fica em `games/urbz-pal/user/lan-host/card.ps2`; no Windows, em `user/lan-host/card.ps2`. LAN e Internet usam a mesma campanha por papel. O amigo recebe uma cópia do cartão ao conectar, na pasta `lan-join`. Se seu cartão anterior for diferente, uma cópia é preservada em `card.ps2.before-net.ps2` antes da substituição. Os cartões offline em `user/card.ps2` ficam separados. Novos cartões são criados vazios e já formatados pelos atalhos.

Após conectar, escolha **2 Player**. Cada pessoa usa o primeiro controle ou teclado do próprio PC. Para retomar, use **Load Game** e selecione os personagens com os respectivos controles. Para salvar, pause com Start (Esc no teclado), escolha **Save → MEMORY CARD slot 1** e confirme **Yes**. Ao sobrescrever, o padrão é **No**, então selecione Yes explicitamente. Aguarde a conclusão antes de fechar. F5/F8 continuam desativados na rede. Os saves não são automáticos a cada frame e não há mesclagem de duas campanhas.

Mantenha o mesmo anfitrião para continuar a campanha. Para trocar, com os jogos fechados, preserve o cartão anterior e copie o cartão de referência para a pasta `lan-host` do novo anfitrião. Backups do runtime ficam em `card.backups`. Em desconexões, cada PC mantém o que conseguiu gravar; na próxima conexão, prevalece o anfitrião. O cartão só é substituído depois da transferência integral, checagem de integridade e backup. Os cartões em memória são comparados ao encerrar normalmente.

A validação usa TCP/TLS real entre processos locais, Linux e o executável Windows via Wine, transferência de cartão, tentativas com chave errada, alteração de registros TLS, fragmentação de pacotes e atraso simulado. Retomada e gravação reais do jogo também foram exercitadas em testes delimitados. Isso não certifica entrada pelo roteador ou uma partida entre duas casas. Nesta rede, o gateway não respondeu à descoberta UPnP e o IPv4 WAN não pôde ser consultado automaticamente; o encaminhamento e a condição de CGNAT continuam dependendo da configuração do roteador/provedor. Windows real, sessões longas e toda a campanha ainda precisam de validação. O carregamento pode ser lento no protótipo.

Para repetir os testes locais de transporte e jogo, use `./Validar-IP-Publico.sh --windows --case wan` ou escolha outro cenário aceito pelo validador. Para cartões compartilhados: `./Validar-Saves-Rede.sh --windows --secure`. Os relatórios recentes estão em `urbz-project/last-direct-ip-validation.json`. Esses comandos exercitam loopback; não testam o encaminhamento do roteador.
