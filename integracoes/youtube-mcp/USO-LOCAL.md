Instalação local do YouTube MCP

Pasta de instalação
C:\Users\Windows\edicao-ia\youtube-mcp

Nome registrado no Codex
youtube_local

A conexão usa launch.ps1 e STDIO. As dez ferramentas de consulta foram preservadas. A inicialização aceita transcrições mesmo enquanto a chave da API está pendente.

Para cadastrar a chave, abra configurar-chave.cmd nesta pasta. A janela recebe a chave e a armazena com criptografia DPAPI vinculada ao usuário do Windows. O inicializador carrega a chave ao iniciar o servidor. Ela também pode vir da variável de ambiente YOUTUBE_API_KEY. Restrinja a chave no Google Cloud à YouTube Data API v3.

A chave exige um projeto Google Cloud com YouTube Data API v3 habilitada. O registro no Codex está pronto. A disponibilidade das ferramentas na conversa depende de o aplicativo recarregar a configuração MCP.

Esta cópia deriva do commit 36142e30de15841139ae9613c568e0bd09aef372 de ZubeidHendricks/youtube-mcp-server, sob licença MIT. As dependências foram atualizadas e fixadas no package-lock.json. A auditoria de instalação registrou zero vulnerabilidades conhecidas.

Foram corrigidos o armazenamento de credenciais no Docker, o transporte HTTP opcional e o consumo de buscas para consultar a última publicação dos canais. HTTP agora requer MCP_HTTP_TOKEN com pelo menos 32 caracteres, autenticação Bearer, limite de corpo de 1 MiB e usa 127.0.0.1 por padrão. O inicializador usado pelo Codex seleciona STDIO.

A verificação scripts/installation-test.mjs testa o inicializador instalado, as dez ferramentas, uma transcrição real, autenticação e limites HTTP. O teste com API simulada preservou filtros e datas de última publicação com uma chamada de busca para dez canais. As consultas adicionais de playlist continuam consumindo a cota correspondente da API.

A pesquisa real e as estatísticas autenticadas aguardam a chave do Google. O mecanismo não calcula os indicadores históricos de outlier e crescimento do vidIQ. A integração com o executor de cortes é uma etapa posterior.
