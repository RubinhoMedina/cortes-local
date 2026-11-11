# Continuidade do projeto de cortes

## Missão e autorização
O usuário quer produção automatizada de vários cortes verticais de vídeos para redes sociais. Trabalhe diretamente no Windows local, usando ferramentas gratuitas já instaladas. Não peça ao usuário para copiar comandos a cada corte. Inspecione e execute por conta própria dentro do projeto, retomando etapas concluídas. Avise antes de qualquer instalação que exija administrador ou qualquer custo. Não publique em redes sociais. Não assuma autorização para assinar serviços pagos.

Primeira entrega solicitada agora: construir e executar um executor reutilizável para este projeto, com logs e retomada de falhas, gerar os demais cortes candidatos e abrir os resultados para revisão. Preserve os originais e o kit. Confirme as possibilidades reais do ambiente local antes de afirmar acesso.

## Máquina verificada
Windows 11 Pro x64, Intel Core i5-5200U @ 2.20GHz, 11,9 GB RAM. Disco C tinha 97,8 GB livres antes do download. O antigo SSD externo passou a ser o disco principal. Não há SSD externo disponível. Meça espaço novamente. Renderize um vídeo por vez, com poucos threads. A transcrição de 16 minutos demorou 1h27min41s neste CPU. Reutilize o JSON existente.

## Caminhos no notebook
Use USERPROFILE, pois o usuário observado foi C:\Users\Windows.
- Kit e modelos de visão: %USERPROFILE%\edicao-ia
- Python isolado: %USERPROFILE%\edicao-ia\.venv\Scripts\python.exe
- Whisper CLI: %USERPROFILE%\edicao-ia\.venv\Scripts\whisper.exe
- Remotion: %USERPROFILE%\edicao-ia\motion
- Trabalho deste vídeo: %USERPROFILE%\cortes-trabalho\001-E07OTlhncP0

Arquivos esperados na pasta de trabalho, a confirmar antes de modificar:
audio.m4a, audio.json (transcrição COMPLETA com tempos por palavra), piloto-fonte.mp4 (39s do original, de 918s até 957s), piloto-enquadramento.mp4 (35s, começa em 4s do piloto-fonte, portanto 922s no original), piloto-legendas.ass, piloto-editado-v1.mp4.

## Ferramentas instaladas e resultados
Git 2.56.0.4, Python 3.11.9 x64, Node LTS 24.20.0, npm/npx 11.19.0, FFmpeg Gyan 9.0.2 com ffprobe e libx265, yt-dlp 2026.10.26, Deno 2.9.8. yt-dlp instalou também outro FFmpeg como dependência. O ativo nos testes era Gyan. Verifique caminhos e versões. Use npm.cmd/npx.cmd no PowerShell para evitar interferência da política de scripts.

No venv estão torch CPU 2.15.0, torchvision 0.29.2, Pillow 13, NumPy 2.4.6, openai-whisper 20250625, MediaPipe 1.2.2, EasyOCR 1.7.2 e suas dependências. pip check passou. Modelo Whisper large-v3-turbo já baixado no cache padrão. Teste de 5s gerou tempos por palavra. Não reinstale sem necessidade.
EasyOCR reconheceu TESTE DE VIDEO 123 com confiança 0,9168. Modelos pt/en já baixados no cache padrão.
MediaPipe detectou 1 rosto na imagem skimage.data.astronaut e gerou mascara-teste.png. Modelos face.tflite e person.tflite estão na pasta edicao-ia. Na máscara, use reshape(image.height,image.width) para remover dimensão extra antes de PIL.Image.fromarray.

## Remotion
Criado com create-video --yes --blank motion. Instalados @remotion/google-fonts e @remotion/paths na mesma versão de remotion, mais simple-icons. Chrome Headless Shell baixado por remotion browser ensure.
Arquivo src/teste-render.tsx criado separadamente com composição Teste3s, 90 quadros, 30fps, 720x1280. Render out/teste-3s.mp4 passou no ffprobe, duração 3s, H264/AAC conforme teste. Template original tinha só 60 quadros.
Commit inicial automático falhou com exit 128. Não invente nome/email global para corrigir. Isso não impediu a renderização.
Há 10 avisos moderados do npm relativos a minimatch, via ESLint e typescript-eslint. npm audit sugeriu downgrade principal do eslint por --force. Não foi aplicado. Avalie atualizações compatíveis com backup do lockfile e teste de render. Não declare o problema resolvido.
Demucs é opcional e ainda não foi instalado. VoiceStudio foi mencionado, mas não foi necessário para este fluxo e não foi inspecionado.

## Fonte e download
URL https://www.youtube.com/watch?v=E07OTlhncP0
Duração aproximada 957s. Reação em inglês ao trailer de GTA 6. No notebook yt-dlp com Deno funcionou para áudio e trechos de vídeo. Neste chat remoto o acesso à página funcionou, mas baixar mídia falhou, mesmo com Node e ejs. Essa limitação é do teste remoto e não deve impedir usar o download local comprovado.
Comando de referência, adapte automaticamente dentro do executor:
yt-dlp --no-playlist --download-sections "*00:01:09-00:01:40" --force-keyframes-at-cuts -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]" --merge-output-format mp4 -P PASTA -o "corte02-fonte.%(ext)s" URL
A fonte baixada era AV1 1080p59.94, e o corte foi recodificado para H264. Considere AVC/30fps e presets leves quando adequado. Não baixe repetidamente arquivos existentes íntegros.

## Piloto validado pelo usuário
piloto-editado-v1.mp4 tem 16,9s, 720x1280, 30fps, H264/AAC. Usuário assistiu e disse que aparentemente falas e legendas estão alinhadas. Isso é validação humana, não prova automática perfeita. Foi escolhido por arco de humor: pergunta se está no jogo, acredita na montagem e depois percebe que é falsa, ameaçando banir quem enviou.
Português nas legendas foi uma decisão do assistente e o usuário aceitou o piloto. Áudio inglês original preservado. Legendas Arial 44, branco e destaques verde, contorno escuro, centro em (360,545), entrada rápida por escala em algumas falas. Os destaques não foram verificados em todos os quadros. Não trate esses efeitos como receita obrigatória.

Problemas conhecidos: enquadramento principal destaca Speed embaixo e jogo em cima; segundo participante parcialmente cortado; o jogo fica pequeno nas trocas de janela; textos da transmissão às vezes ficam atrás do rosto. Corrija por trecho quando necessário. Não aplique crop central indiscriminadamente. Não amplifique a imagem por conversões sucessivas se puder renderizar direto da fonte.

Crop da prévia que foi aceito como base, não como regra universal:
[0:v]split=2[jogo][pessoas];[jogo]crop=1440:810:0:100,scale=720:405,pad=720:560:0:77:black[topo];[pessoas]crop=780:540:0:540,scale=1040:720,crop=720:720:0:0[baixo];[topo][baixo]vstack=inputs=2,fps=30,setsar=1[v]

Timeline final do piloto, em segundos RELATIVOS ao piloto-enquadramento.mp4:
0–3.8, 6.7–10.1, 12.3–15.1, 28–34.9. Concatenados nessa ordem. Foram usados fades de áudio de 8ms nas pontas das junções, sem transição visual. Para converter ao original, somar 922s. Reutilize o ASS existente em vez de recriar sua tradução às cegas.

## Próximos candidatos editoriais
São hipóteses extraídas da transcrição. Conferir visual e áudio, preservar contexto e não prometer viralização.
- 70–98.5s: confunde Franklin, Lester e Michael. Próximo corte a produzir, baixar com margem 69–100s.
- 237–260.8s: comparam personagem com ele e ele discorda.
- 346–368.1s: os dois gritam que estão no jogo.
- 468–481.3s: fica feliz e mal consegue falar.
- 672–689.4s: reação à data antiga exibida no trailer. Identificar claramente como reação da época, não notícia atual de lançamento.
- 883–907.1s: insiste que Lucia é brasileira. Tratar como especulação/brincadeira do participante, não como fato.
- Piloto já concluído em 922–956.9s.
Pode haver outros candidatos. A história de Watkins Auto Parts e a ligação ao pai são alegações do vídeo, não fatos históricos verificados. Não transformar em notícia comprovada.

## Objetivo do executor
Preferir Python/FFmpeg com configuração editável e launcher Windows simples, aproveitando venv e yt-dlp existentes. Use Remotion onde de fato ajudar nas legendas/motion. Um lançamento deve concluir o lote, sem solicitar ao usuário comandos por etapa. Registrar fontes, intervalos absolutos, intervalos editados e legendas em arquivos para reprocessar só o necessário. Validar existência, duração, áudio, resolução e decodificação de cada export. Não dizer que corte automático de respirações, seleção semântica e tradução estão prontos só por haver Whisper instalado. Para novos links, declarar o que é heurístico e o que depende de seleção/revisão editorial. O lote atual tem seleção já proposta.

## Drive e limpeza
Usuário decidiu editar localmente, revisar, enviar o projeto ao Drive, verificar cópia e só então apagar a pasta temporária específica. Automação de upload/limpeza AINDA NÃO FOI IMPLEMENTADA nem testada. Não excluir nada agora. Preserve kit, modelos, fontes e arquivos necessários para reabrir projeto.
O plugin Drive desta conversa foi autorizado e criou pastas. Não assuma que autorização está disponível ao Codex local. Verifique conectores antes de pedir nova autenticação. Se necessário, configure OAuth próprio sem pedir senha/tokens no chat. rclone copy seguido de verificação por hash é opção proposta, não instalada. Uma falha de upload/check deve bloquear limpeza. Teste limpeza com pasta descartável antes de ativar para vídeos reais. Evite sincronização bidirecional com exclusão propagada.
Pasta raiz criada: https://drive.google.com/drive/folders/1fuWrmZsPbXuZ4i2FQ5MJCvPpnQSOE0Ek
Projeto: https://drive.google.com/drive/folders/1bXc6dqZBowkjRZpzEJ9muaj8TxPLku0F
Subpastas verificadas:
01 - Original: 1xYkmwRL4RKHgTbL2O82M3uPHU6ArRTN8
02 - Transcrição e marcações: 1RVUWvPqWEj8wThplFpfDp839V08h_z9w
03 - Hooks e referências: 15J0jAgaa4mCEqPeAZxG-ky7UGkHT3sOd
04 - Cortes em revisão: 16yaXqH34z3C-AsU36nXVptP09_yD4HQT
05 - Cortes finais: 1a4AZGGAJBOUGTTZIShB5PNJeghKKdxMU
Nenhum MP4 foi enviado a essas pastas até este handoff. Apenas estrutura foi criada. Não criar estrutura duplicada.

## Comece agora
1. Inspecione os caminhos locais e arquivos esperados. Leia audio.json e ASS. Confirme ferramentas sem reinstalar.
2. Construa executor e launcher reutilizáveis na pasta do projeto, preserve os arquivos existentes e evite alterações globais.
3. Gere corte02 com legenda traduzida natural e contexto fiel. Examine imagens e valide áudio/tempos. Depois gere os demais candidatos que tiverem arco completo.
4. Abra exports para revisão. Só depois cuide de upload verificado e da limpeza autorizada, com logs e verificações restritas ao projeto.
