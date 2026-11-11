# Lotes grandes — versão 2

O campo aceita um tema ou um pedido simples, por exemplo: **encontre os vídeos mais viralizados do GTA6 e me entregue 100 cortes**. O plano mostrado antes de iniciar deve indicar **Pesquisa: GTA 6 · Meta: 100 cortes**. A interpretação usa regras locais para tema e quantidade; não é uma conversa com um modelo de linguagem.

O campo numérico de meta substitui a quantidade escrita no pedido. A meta padrão, quando nenhuma quantidade é informada, é 12. Podem ser planejadas metas de 1 a 1000, respeitando o conteúdo encontrado. Isso não é uma promessa de quantidade ou viralização.

## Controle do lote

- O controlador pesquisa fontes em rodadas com consultas diferentes e intercala canais. Busca novas fontes quando faltam cortes.
- O plano mostra os limites de fontes, duração e rodadas; o teto de candidatos por vídeo pode ir até 50. O padrão agora é 20 candidatos, com seleção por pontuação e qualidade, e não quatro cortes obrigatórios.
- Cada fonte e cada corte são executados em sequência. Fontes e candidatos com falhas são repetidos de forma limitada e substituídos por outros candidatos quando necessário.
- Cada vídeo validado entra imediatamente na revisão e é salvo no banco. Não é necessário esperar o lote inteiro para assistir aos resultados.
- A prevenção de repetições considera a origem, a sobreposição dos tempos e similaridade das falas. Não é um detector perfeito de duplicação semântica ou visual.
- Ao atingir a meta, o lote para. Se esgotar o plano antes, termina com **Meta parcial** e explica o motivo. **Buscar mais fontes** amplia o plano, até os limites exibidos.
- Com um link específico, o lote usa somente aquele vídeo. Uma meta grande pode não caber nessa fonte; para pesquisar outras, use um plano sem link.

## Pausa e recuperação

**Pausar** encerra a operação atual e preserva o que está pronto. **Retomar lote** continua com o mesmo identificador, reaproveitando transcrição, mídia e resultados válidos. Ao abrir novamente o aplicativo depois de uma interrupção inesperada, os lotes que estavam em fila/processamento são retomados automaticamente. Lotes pausados ou cancelados pelo usuário aguardam retomada explícita.

O Windows agrupa o servidor e seus processos filhos para que uma interrupção não deixe uma edição antiga segurando arquivos. O computador permanece ativo durante o processamento, mas fechamento da tampa, suspensão manual, queda de energia e políticas do Windows ainda podem interromper o trabalho. A retomada depende de abrir o aplicativo novamente.

O lote pausa se restar menos de 1,5 GiB no disco. Nenhuma limpeza é automática. Antes de apagar qualquer arquivo do projeto, validar upload e integridade no Drive.

## Limites que continuam existindo

A pesquisa pública do YouTube pode limitar pedidos, exigir verificação ou indisponibilizar fontes. Após falhas repetidas, o lote preserva os resultados e mostra a necessidade de retomada. A transcrição e a tradução continuam locais; esta instalação traduz inglês e português. Outros idiomas são ignorados com uma observação.

As notas são heurísticas. Contexto, nomes, fatos, enquadramento e tradução continuam sujeitos à revisão humana. A análise de referências cobre apenas sua abertura falada. Não há publicação automática, assinatura nova, API paga ou geração de imagem cobrada pelo fluxo.

O teste de uma meta de 100 valida o controlador em cenário simulado. A verificação real desta atualização produziu vídeos pequenos e testou interrupção/reinício. Não significa que 100 vídeos reais já tenham sido produzidos.

Referência técnica do controle de processos: [Windows Job Objects — Microsoft](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
