# Cortes Local

Sistema interno de pesquisa no YouTube, seleção e produção de cortes, com revisão humana. Backup privado da instalação validada no Windows. Não adicionar colaboradores nem alterar a visibilidade sem autorização do proprietário.

## Lotes grandes — versão 2

Pedidos como **encontre vídeos de GTA6 e me entregue 100 cortes** são convertidos em tema e meta antes de iniciar. Há pesquisa incremental, fila persistente, deduplicação por tempo/fala, pausa, retomada automática após interrupção e resultados parciais com motivo explícito. Leia `docs/LOTES-GRANDES.md`.

O frontend compilado atual está em `app/frontend/bundle.zip.b64`, com SHA-256. O restaurador aplica o código atual e essa interface depois dos volumes de base, para não recuperar uma interface antiga. Os volumes de vídeo/modelos continuam como snapshot validado anterior; novos lotes criados no computador não são sincronizados automaticamente com o GitHub.

## Conteúdo

- `app/`: painel React, servidor local Python, fila, pesquisa, tradução, análise das aberturas de referências, textos e capas.
- `motor/`: executor, seleção, enquadramento, configurações, legendas e transcrição do piloto validado.
- `integracoes/youtube-mcp/`: código instalado do MCP do YouTube, com os ajustes de segurança e sua licença original. O painel usa yt-dlp e funciona sem a chave desse MCP.
- `backup/`: instalação, modelos ativos, lotes, fontes e resultados, em partes de até 20 MiB; cada parte e arquivo possui SHA-256 no manifesto.
- `docs/`: instruções operacionais e versões das dependências.
- `restaurar.py`: verifica e extrai as partes em uma pasta vazia, sem sobrescrever a instalação em uso.

## Recuperar os arquivos

Baixe ou clone **o repositório inteiro**, incluindo todas as partes de `backup/`. Com Python 3.11, execute:

```powershell
python restaurar.py --destino C:\Recuperacao-Cortes-Local
```

O restaurador confere todos os hashes, o ZIP e os arquivos extraídos. Não apaga os originais. Leia `docs/RESTAURACAO.md` antes de colocar os arquivos recuperados em uso.

## Limites e privacidade

Não contém chaves, senhas, cookies, tokens, configurações completas do Codex ou credenciais do Windows. Credenciais precisam ser reconectadas pelo proprietário. Ambientes Python/Node e executáveis de terceiros são reinstalados a partir das versões e fontes documentadas; não são portáveis por simples cópia. O modelo Whisper grande opcional e o runtime Qwen/llama.cpp abandonado não estão nos volumes; o fluxo padrão usa Whisper base e Argos, incluídos.

As notas são heurísticas; não garantem viralização. A análise das referências cobre a abertura falada, até 20 segundos, sem uma análise visual completa. A revisão de contexto, fatos e tradução é humana. GPT Image é opcional; não há chamada automática a serviço pago nem publicação automática.

Não remova arquivos locais antes de validar backup e integridade no Drive, conforme a regra operacional do projeto. Este envio ao GitHub não executa limpeza nem substitui essa verificação do Drive.
