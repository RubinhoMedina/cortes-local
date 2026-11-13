# Layout React Flow opcional

O painel oferece `Cortes tradicionais` (padrão preservado) e `React: ator Flow em cima, gameplay embaixo`.

O modo `flow_react` exporta H.264/AAC, 720×1280, 30 fps. A metade superior usa um MP4 separado gerado no Flow; a inferior usa a fonte do corte. A faixa central tem o texto informado ou o hook editorial. A única trilha de áudio vem do MP4 Flow. A transcrição da fonte não vira legenda da fala do ator. Não chama Voice Studio nem outro TTS.

## Cadastro local

Coloque um MP4 Flow com vídeo e áudio em `data/react-assets` com nome simples, por exemplo `ator-headset.mp4`. Reabra a página e selecione o ator. O HTTP só aceita o ID `ator-headset`, nunca um caminho local, URL ou upload. O arquivo é copiado para `data/<job>/assets/flow-actor.mp4`; o lote fixa o hash e a duração. Retomadas usam essa cópia. A disponibilidade de uma trilha de áudio não comprova que existe fala: confira o vídeo no Flow antes de produção.

O ativo inicial `neyboca-previa-sem-fala` é uma prévia de reação existente, sem fala validada. Serve para avaliar a composição; substitua por um ator Flow com a fala desejada para produção narrada.

Os candidatos precisam caber na duração do ator. O fluxo filtra os maiores e o executor também rejeita um corte maior; não repete a fala nem estende o áudio artificialmente. O modo tradicional continua com seu áudio e enquadramento anteriores.

## Fonte local do Drive no fluxo canônico

O renderizador também aceita a fonte local via catálogo `sources` existente no JSON do `fluxo.py`: `{"path":"gameplay-drive.mp4","start":0,"end":<duracao_real>}`. O painel de pesquisa continua usando links YouTube; esta mudança não cria uma nova importação de Drive.

No corte use `"layout":"flow_react"`, `"flow_actor":"assets/flow-actor.mp4"` e `"seam_text":"Texto central"`. O ator deve estar dentro da pasta do executor/lote; caminhos absolutos, fora da pasta ou URLs são rejeitados. `--auto-frame` não executa o analisador de cenas neste modo. O recibo inclui o SHA-256 do ator e dos executores, invalidando a reutilização quando qualquer entrada muda.
