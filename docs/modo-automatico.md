# Lote de cortes no Windows

Abra executar.cmd para processar todos os cortes de lote.json e abrir a pasta revisao.
Para retomar um corte específico, rode executar.cmd --only 2. Use --no-open para execução sem abrir o Explorador. A opção --config aceita outro JSON com o mesmo esquema.

Edite os tempos absolutos em edit e as traduções em lines. Há uma tradução por segmento de áudio selecionado. O executor obtém os tempos do JSON de transcrição e grava o ASS já convertido para a timeline editada. Os tempos start e end delimitam a janela baixada e devem abranger todos os intervalos de edit.

O layout split combina a cena e as reações. Os campos opcionais scene_crop e reaction_crop usam [largura, altura, x, y] na referência 1920 × 1080. O layout full mantém o quadro inteiro. O layout reaction usa só a região da reação. O texto opcional title é exibido no topo do corte.

O lote baixa e renderiza um corte por vez. O cache fontes é indexado pelo URL e pela janela de download. Um download inválido é preservado com nome de falha e pode ser baixado novamente. Cada export tem um JSON com os dados da edição e hashes SHA-256. O lote reaproveita os exports validados quando os hashes e a configuração coincidem. Consulte lote.log para ver falhas e comandos. O processo retorna código 1 se algum corte falhar.

Para outro vídeo, forneça a transcrição Whisper em JSON, marque os intervalos e escreva as traduções. A seleção editorial e as traduções deste projeto foram feitas para estes cortes. O executor depende de FFmpeg/ffprobe e yt-dlp no PATH e do Python do kit edicao-ia.

A pasta revisao contém material para aprovação. O piloto, o áudio original e a transcrição permanecem na pasta do projeto. Upload e limpeza não fazem parte do launcher.


## Modo automático local

Abra executar-automatico.cmd para selecionar até seis candidatos da transcrição e renderizar em revisao-automatica. O lote usa automacao.json para definir duração, quantidade, termos do tema e fontes locais conhecidas. A seleção mantém sua configuração editável em analise/lote-automatico.json.

A seleção é heurística. Ela pontua termos do tema, perguntas, reações, repetições e limites de frases. A pontuação serve para ordenar candidatos e exige revisão editorial. Pausas maiores que 2,5 segundos podem ser encurtadas, mantendo margem de áudio nas pontas. Os tempos absolutos e os intervalos editados ficam registrados no JSON.

As traduções já aprovadas são reaproveitadas quando todas as falas de um candidato têm tradução disponível. Outros candidatos recebem as legendas no idioma da transcrição, com translation_status indicando a revisão pendente. O modo automático usa o JSON Whisper existente.

O enquadramento amostra uma imagem a cada dois segundos. Ele usa o MediaPipe e o modelo face.tflite já existentes no kit, com foco nos participantes da região inferior esquerda deste projeto. Conserva o enquadramento-base quando a evidência é insuficiente. Os recortes manuais reaction e full têm prioridade. Outros formatos de vídeo exigem configurar e conferir seu enquadramento.

A análise usa CPU local, uma fonte por vez e dois threads no FFmpeg. Seleção, análise de cenas e validação das fontes têm cache, verificado por hash. A primeira análise acrescenta tempo de processamento. A retomada reutiliza os vídeos e as análises válidas. O modo existente continua disponível em executar.cmd.

Para gerar somente o JSON de candidatos, use o Python do kit com fluxo.py --auto-select --analyze-only. Para aplicar o enquadramento automático aos intervalos do lote validado, use fluxo.py --auto-frame. A opção --only aceita os IDs desejados. Para renderizar ajustes feitos no JSON de candidatos, use fluxo.py --config analise/lote-automatico.json --auto-frame.

Logs do novo modo ficam em automatico.log, e os comandos FFmpeg também aparecem em lote.log. O resumo de tempos da execução fica em analise/ultima-execucao.json. Use --no-open para executar sem abrir o Explorador. O código 1 indica falha em pelo menos um candidato.

A descoberta de vídeos no YouTube e a tradução automática de falas novas são etapas adicionais ao modo implementado. O fluxo local utiliza transcrição, seleção, enquadramento e renderização sem chamadas a APIs pagas.
