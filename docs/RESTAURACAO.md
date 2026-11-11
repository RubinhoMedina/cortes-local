# Restauração

1. Execute `python restaurar.py --destino PASTA_VAZIA`. Guarde todas as partes originais. Isso reconstrói a estrutura relativa ao perfil do Windows: `edicao-ia`, `cortes-trabalho` e `.cache/whisper/base.pt`.
2. Compare os arquivos recuperados com a instalação existente. Para recuperar a instalação padrão, as pastas precisam ocupar os caminhos equivalentes dentro de `%USERPROFILE%`. Não sobrescreva uma instalação mais recente sem preservar sua cópia.
3. Instale Python 3.11 e, se for reconstruir o frontend ou MCP, Node compatível com os arquivos package-lock. FFmpeg/ffprobe, yt-dlp e Deno devem ser instalados de fontes oficiais. Nada disso é instalado pelo restaurador.
4. Recrie `%USERPROFILE%\edicao-ia\.venv`. Instale a versão CPU do PyTorch usando seu índice oficial e as dependências de `requirements-runtime.txt`. `docs/ambiente-python-completo.txt` registra o ambiente observado. Não copie um venv entre usuários/computadores como substituto da reinstalação.
5. O pacote Argos e seus arquivos extraídos, o modelo de visão e Whisper base estão nos volumes. O modelo opcional `large-v3-turbo` pode ser obtido pelo próprio Whisper apenas se necessário; seu download é grande.
6. Recrie `edicao-ia/cortes-app/tools.json` com os caminhos de `Get-Command ffmpeg`, `ffprobe`, `yt-dlp` e `deno`. Há um exemplo estrutural em `docs/tools.example.json`; os caminhos variam por instalação.
7. Em outro usuário ou diretório, ajuste os caminhos absolutos salvos no banco SQLite e nos catálogos/configurações, além de `iniciar.cmd`. O backup é uma cópia fiel do perfil original. O Python do servidor é localizado em `edicao-ia/.venv`, e o motor em `%USERPROFILE%/cortes-trabalho/001-E07OTlhncP0`.
8. O frontend compilado validado também está nos volumes; para recompilar, entre em `app/frontend` e use `npm.cmd ci` e `npm.cmd run build`. Para o MCP, use os mesmos comandos na pasta da integração e configure sua chave separadamente. Nenhuma credencial está incluída.
9. Abra `iniciar.cmd` e confira lotes, arquivos e reprodução. Recrie o atalho da área de trabalho apontando para `iniciar.pyw` por meio do Python local.

Este processo não publica vídeos, não altera permissões do GitHub e não apaga arquivos. Não utiliza Git LFS nem serviços de backup pagos.
