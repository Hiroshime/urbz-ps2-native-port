# The Urbz — PS2 Native Port

Protótipo de recompilação nativa de **The Urbz: Sims in the City**, edição europeia de PS2, para Linux e Windows, com multiplayer experimental por rede.

**A proposta é distribuir as ferramentas, não o jogo.** Cada usuário deve possuir uma cópia do jogo adquirida legitimamente e fornecer sua própria ISO compatível. O utilitário lê essa ISO, traduz e compila o código localmente e gera um executável para PC com o suporte multiplayer deste projeto. Ele não modifica a ISO original. O repositório não fornece a ISO, arquivos extraídos ou um executável pré-compilado do jogo, nem indica onde obter esses arquivos.

Fluxo pretendido: **sua cópia do jogo → sua ISO compatível → compilação local → jogar offline ou conectar dois jogadores pela rede**. Cada participante precisa preparar sua própria cópia e usar builds compatíveis. Esse é o fluxo do projeto; a reprodução completa a partir de um clone limpo ainda precisa ser validada, conforme a seção de compilação abaixo.

O foco atual é preservar a velocidade original da edição PAL, os saves e o modo de dois jogadores. A cena de gameplay validada produz aproximadamente **25 imagens novas/s com vídeo a 50 Hz**. Não há modo de 60 FPS certificado.

> **Em desenvolvimento.** A primeira área, abertura e alguns fluxos de salvamento foram testados. A campanha completa, duas máquinas físicas e uma conexão real pela Internet ainda não foram validadas. O executável Windows foi testado via Wine; os launchers PowerShell precisam de teste em Windows real.

## Conteúdo

- [Estado atual](#estado-atual)
- [Como funciona](#como-funciona)
- [Cópia compatível do jogo](#cópia-compatível-do-jogo)
- [Requisitos e compilação](#requisitos-e-compilação)
- [Jogar e salvar](#jogar-e-salvar)
- [Multiplayer](#multiplayer)
- [Gráficos e desempenho](#gráficos-e-desempenho)
- [Validação e documentação](#validação-e-documentação)
- [Contribuições e publicação](#contribuições-e-publicação)
- [Créditos e licença](#créditos-e-licença)

## Estado atual

| Recurso | Estado observado |
|---|---|
| Linux x86-64 / Vulkan | Primeira área executada no Nobara |
| Windows x86-64 | Compilação cruzada e execução via Wine/Vulkan |
| Dois jogadores locais | Tela dividida original e comandos independentes |
| Controles | SDL2; testes automatizados com controles virtuais |
| Save nativo | Gravação e retomada verificadas em trechos específicos |
| Rede | Lockstep TCP com um jogador por PC; testes em loopback |
| Internet direta | Transporte TLS implementado; acesso externo ainda não confirmado |
| Gráficos | Perfis opcionais de 1× a 4×; FSR1 e saída Quad HD |
| Widescreen | Câmera 16:9 e proporção do HUD corrigidas na cena testada |
| Fluidez original | Mantida na cena medida com o launcher Linux em 2× |
| 60 FPS e texturas HD | Sem modo suportado nesta versão |

Não há rollback, reconexão, lista pública de salas ou servidor de lobby. A sincronização ainda não certifica o estado de todos os dispositivos do PS2 ou toda a campanha.

## Como funciona

O tradutor transforma o código do processador EE do PS2 em C++ e o compila para o PC. O runtime recria os serviços necessários do console, incluindo IOP, unidades vetoriais, áudio, entrada e gráficos. A apresentação gráfica usa Vulkan ou os backends disponíveis do runtime.

A base é [ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp), revisão `5d1ebbcf133cb3c31df75a294dbe38e30734c1ce`, derivada de [ps2-web-recomp](https://github.com/snuri00/ps2-web-recomp). Este repositório acrescenta o trabalho específico de integração e validação do Urbz. A [documentação original](README-UPSTREAM.md) foi preservada; as afirmações sobre outros jogos pertencem ao projeto de origem.

## Cópia compatível do jogo

Cada jogador deve possuir sua própria cópia do jogo adquirida legitimamente e fornecer a imagem compatível dessa cópia. **A compra ou posse do jogo não faz parte deste utilitário: este repositório não fornece o jogo, a ISO ou links de download do jogo.**

| Identificação | Valor |
|---|---|
| Região | Europe / PAL, multilíngue |
| Serial | `SLES-52908` |
| Executável no disco | `SLES_529.08` |
| Tamanho da ISO | `4461363200` bytes |
| SHA-256 da ISO | `62bfa4db0ae21b7b67043c4fca59025324e55ad5d59d3fdbae1e902aff43d07e` |

Outras regiões e revisões não foram validadas. ISO, arquivos extraídos, C++ gerado a partir do jogo, executáveis recompilados, screenshots, gravações e saves ficam fora da publicação. Os hashes e endereços de integração identificam a revisão; não substituem os arquivos do jogo.

## Requisitos e compilação

### Linux

- Git, Bash 4+, CMake 3.20+, Ninja e Python 3.11+ acessível como `python` e `python3`.
- Clang com C++20, `<format>` e os builtins vetoriais exigidos pelo projeto; GCC e MSVC não são suportados.
- Headers e biblioteca SDL2, driver Vulkan e **OpenSSL 3.5.9 ou mais recente** com headers de desenvolvimento.
- Os executáveis locais validados exigem AVX2. O ambiente medido foi Ryzen 7 7800X3D e RTX 4070 SUPER; não é uma especificação mínima universal.

Obtenha as fontes e prepare a compilação:

```bash
git clone https://github.com/Hiroshime/urbz-ps2-native-port.git
cd urbz-ps2-native-port
# Opcional: indique seu Clang compatível.
export CXX=/caminho/para/clang++

bash scripts/setup.sh --native-only
./Construir-Linux.sh "/caminho/para/sua-copia-PAL.iso"
./Jogar-Linux.sh
```

Os scripts respeitam `CXX` e podem usar as dependências instaladas no sistema. Uma toolchain local previamente extraída do Hookshot é usada quando disponível, mas o AppImage não acompanha o código e não é um requisito do projeto. Bibliotecas e ferramentas baixadas ficam em pastas ignoradas. O primeiro preparo pode exigir rede.

**Limite de reprodução:** o checkout público não inclui os snapshots, gravações VU, overlays ou caches derivados do jogo usados nos testes locais. A compilação inicial e a descoberta de código precisam ocorrer a partir da cópia do usuário; um clone limpo ainda não foi validado até o mesmo ponto da cidade. Não há instalador público pronto. Consulte também o [fluxo original de compilação](README-UPSTREAM.md#get-started-on-linux).

### Windows

O caminho exercitado é a compilação cruzada a partir do Linux, depois de preparar os fontes gerados do jogo:

```bash
./Construir-Windows.sh
./Empacotar-Windows.sh
```

O compilador Windows e o OpenSSL estático são preparados pelos scripts, com versões e hashes fixados. O resultado local fica em `dist/Urbz-PS2-Windows`. **Esse pacote contém a ISO local e código recompilado do jogo: não o publique como release.** O pacote serve apenas para testes locais com a cópia fornecida pelo usuário.

Não há validação de compilação do fork inteiro diretamente em Windows. Instruções genéricas upstream não equivalem a um procedimento Windows certificado para este protótipo.

## Jogar e salvar

```bash
./Jogar-Linux.sh
./Configurar-Graficos.sh
./Jogar-Linux.sh --graficos hd
```

No pacote Windows local, use `Jogar-Windows.cmd` e `Configurar-Graficos.cmd`. Selecione **2 Player** no próprio jogo para o modo local. Cada controle corresponde a um jogador; F1 mostra as opções de entrada offline. A compatibilidade ampla com controles físicos ainda requer playtests.

- **Save / Load Game:** usam o cartão de memória e o fluxo original do jogo.
- **F5 / F8:** snapshots offline do runtime; não substituem o save nativo.
- **F2:** alterna o filtro da apresentação.

Os arquivos pessoais Linux ficam em `games/urbz-pal/user`; no pacote Windows, em `user`. Esses arquivos são ignorados pelo Git.

## Multiplayer

O modo de rede sincroniza os comandos dos dois jogadores e mantém a tela dividida original nos dois PCs. Cada pessoa usa o primeiro controle ou teclado da própria máquina. Ambos precisam da mesma ISO e de executáveis compatíveis.

### Rede local

```bash
# Jogador 1
./Hospedar-LAN.sh --graficos hd

# Jogador 2
./Entrar-LAN.sh 192.168.1.20 --graficos hd
```

Os atalhos LAN simples destinam-se a uma rede privada de confiança. Leia [LAN.md](urbz-project/LAN.md) para controles, atraso de comandos, diagnóstico e saves.

### Internet por IPv4 público

```bash
./Hospedar-Internet.sh --graficos hd
./Entrar-Internet.sh IP_PUBLICO_DO_AMIGO --graficos hd
```

O anfitrião fornece IP e chave da partida. Os atalhos de Internet usam TLS autenticado antes de transferir o cartão. É necessário encaminhar **TCP 27888** no roteador e ter IPv4 acessível; CGNAT pode impedir a entrada direta. Não é necessário servidor na nuvem ou VPN nesse método. A conexão real entre casas ainda não foi validada. Veja [INTERNET.md](urbz-project/INTERNET.md).

### Compatibilidade e progresso

Use a mesma resolução interna, filtro 2D e proporção widescreen nos dois lados. O filtro final da imagem pode variar. O cartão compartilhado do anfitrião é a referência; o cliente recebe uma cópia antes da partida e seu cartão anterior é preservado em backup. Salve pelo menu do jogo. F1 e snapshots ficam desativados na sessão de rede.

## Gráficos e desempenho

| Perfil | Configuração |
|---|---|
| `padrao` | Preserva resolução e filtros existentes |
| `original` | Resolução interna 1× |
| `hd` | Resolução interna 2× com filtros |
| `alto` | Resolução interna 3× com filtros |
| `ultra` | Resolução interna 4× com filtros |
| `qhd` | Interno 2×, saída 2560×1440 e FSR1 EASU/RCAS |

Aumentar a resolução define o tamanho interno da renderização; 2× não significa automaticamente saída 1080p. As texturas permanecem originais.

Para experimentar FSR1 em Quad HD e widescreen: `./Jogar-Linux.sh --graficos qhd --wide --fullscreen`. Sem `--wide`, a imagem conserva 4:3. No pacote Windows: `Jogar-Windows.cmd -Graphics qhd -Widescreen -Fullscreen`. O filtro é opcional e não gera quadros nem texturas novas. Consulte [FSR.md](urbz-project/FSR.md) e [WIDE-QHD.md](urbz-project/WIDE-QHD.md) para os controles de saída e proporção.

O launcher Linux com FSR1, widescreen e saída QHD mediu **50,13 atualizações/s** na cena em 2×, com 255 imagens novas em 510 atualizações: aproximadamente a fluidez original PAL de 25 imagens/s. Um benchmark sequencial separado mediu ganho de 3,61× em 2× contra o executável anterior. Isso não certifica desempenho em todas as áreas ou GPUs. 4× ficou abaixo da capacidade necessária nesse benchmark.

O alvo atual é **preservar a fluidez original**, não forçar 60 FPS. Os experimentos de desbloqueio ficaram separados dos launchers. Detalhes em [GRAFICOS.md](urbz-project/GRAFICOS.md) e [DESEMPENHO.md](urbz-project/DESEMPENHO.md). Capturas e gráficos locais mencionados nesses documentos não acompanham o checkout público.

## Validação e documentação

| Evidência local | Resultado |
|---|---|
| Compatibilidade gráfica em rede | 14 casos anteriores e 6 casos novos de FSR/proporção aprovados |
| FSR e saída QHD | Imagem final 2560×1440 capturada nos dois builds; simulação preservada |
| Widescreen | Campo de visão ampliado e geometria de personagens/HUD verificada na cena local |
| Abertura Linux/Windows via Wine | 1.200 frames, 40 comparações de estado iguais |
| Save pelo menu com janelas e TLS | 1.300 frames, 43 comparações iguais, cartões finais idênticos |
| Controles virtuais SDL2 | 62 verificações aprovadas na validação anterior |
| Arquivos de saves/snapshots | 85 verificações aprovadas na validação anterior |

Esses são resultados locais, não um selo de compatibilidade da campanha. Os relatórios versionados identificam os executáveis medidos; hashes históricos podem diferir do build mais recente. Alguns testes exigem fixtures locais não distribuídas.

```bash
./Validar-LAN.sh --windows --windowed
./Validar-Multiplayer.sh --windows --gameplay
./Validar-Saves-Rede.sh --windows
python3 scripts/prepare_urbz_github.py --check
```

- [Estado e limitações](urbz-project/STATUS.md)
- [Guia local](urbz-project/LEIA-ME.md)
- [Identificação do jogo](urbz-project/game.json)
- [Manifesto dos builds locais](urbz-project/build-manifest.json)
- [Última validação de desempenho](urbz-project/last-performance-validation.json)
- [Validação FSR, QHD e widescreen](urbz-project/last-fsr-wide-validation.json)

O workflow de fontes verifica publicação, sintaxe Python e Bash sem a ISO. O workflow de compilação herdado permanece manual e exige as dependências adequadas; não foi executado no GitHub para este fork.

## Contribuições e publicação

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para relatar problemas e contribuir, e [PUBLICACAO.md](urbz-project/PUBLICACAO.md) para preparar o envio. Não anexe arquivos extraídos, saves, snapshots ou dados de conexão privados em issues. Descreva sistema, revisão, cenário e resultado esperado.

## Créditos e licença

- **Samir Nuri / ps2-web-recomp:** base original.
- **exoteric33 / ps2-native-recomp:** tradutor e runtime de origem, com créditos adicionais em [README-UPSTREAM.md](README-UPSTREAM.md#credits-and-license).
- **SDL2, wgpu-native, LLVM, DXC e OpenSSL:** dependências; avisos disponíveis em [urbz-project/licenses](urbz-project/licenses).
- A investigação de patches comunitários está documentada em [FPS-INVESTIGACAO.md](urbz-project/FPS-INVESTIGACAO.md), com atribuição ao autor.

O código deste repositório segue a [licença MIT](LICENSE), preservando os avisos originais. Isso não licencia os arquivos ou o código do jogo. Projeto independente, sem afiliação ou endosso de EA, Maxis, Sony ou Nintendo.

O filtro FSR1 deriva do código MIT da AMD; consulte [a licença](third_party/fsr1/LICENSE) e [a revisão usada](third_party/fsr1/UPSTREAM.md).
