# Cortes Local

Abra o atalho **Cortes Local** na área de trabalho. O painel abre no navegador em http://127.0.0.1:3781. Depois da inicialização pelo atalho, o uso do painel não exige abrir o Codex.

## Uso

1. Informe o tema, por exemplo **GTA 6**, e clique em **Iniciar pesquisa**.
2. Aguarde as etapas de pesquisa, transcrição, textos e edição. Pode fechar a página; o computador deve permanecer ligado e acordado.
3. Abra o lote em **Revisão** e assista aos cortes. Confira contexto, tradução, nomes e afirmações antes de aprovar.
4. Copie título, hook, descrição e tags. Os campos de título e descrição podem ser editados e salvos.
5. Em **Capas**, escolha entre três quadros reais do corte. O briefing para GPT Image é apenas texto para copiar; a ferramenta não chama uma API paga.
6. Use **Baixar pacote** para obter o MP4, as três capas, os textos e as referências em ZIP. A escolha da capa também fica registrada nos dados do pacote.

Em **Preferências do lote**, escolha até três fontes, o limite de candidatos por fonte e a duração máxima. O limite não é uma promessa de quantidade: fontes indisponíveis ou ausência de candidatos podem produzir menos cortes. Há também um campo opcional para um link específico do YouTube.

Se um lote falhar ou for interrompido, use **Retomar lote**. Arquivos e análises em cache são reaproveitados. **Cancelar lote** solicita a parada; uma tradução em andamento pode terminar antes de o cancelamento ser aplicado.

## O que funciona automaticamente

- Pesquisa pública no YouTube, classificação de candidatos e busca de referências curtas.
- Análise local da abertura falada de até três referências, limitada aos primeiros 20 segundos, com identificação de pergunta, reação verbal ou afirmação. O padrão predominante ajuda a escolher o hook entre as falas do próprio corte. Áudios e resultados ficam em cache.
- Download do áudio quando necessário e dos intervalos de vídeo selecionados.
- Uso de legendas disponíveis; transcrição local com Whisper quando não há legendas utilizáveis.
- Seleção por termos, perguntas, reações, repetições, duração e limites de frase.
- Tradução local de fontes em inglês, reaproveitando traduções já validadas do piloto quando disponíveis.
- Edição vertical em 720 × 1280, legendas, hook na imagem, ajuste de enquadramento por cenas e validação dos arquivos exportados.
- Preparação de título, hook, descrição, tags, três opções de capa e pacote de revisão.

## Como interpretar as notas

A nota de pesquisa é uma comparação entre os vídeos da amostra consultada. Usa relevância do título e visualizações; quando há datas, considera a média de visualizações por hora desde a publicação. Quando há observações do mesmo vídeo separadas por pelo menos uma hora, pode usar a velocidade medida entre essas observações. **Média histórica não é velocidade atual.**

A nota editorial é uma heurística das falas. Ela ajuda a ordenar a revisão, mas não foi calibrada como previsão de viralização. As referências registram títulos, canais, métricas públicas e, quando o áudio está disponível, um trecho da abertura transcrito automaticamente. Esta versão não realiza uma análise visual completa de cada Short de referência nem replica o sistema de outliers do vidIQ. Os textos são montados a partir das falas; podem ficar simples e precisar de ajustes.

O enquadramento segue o piloto de reação, com análise de rostos e cenas. Outros formatos e posições de câmera podem exigir adaptação. Tradução automática pode errar gírias e nomes e pode usar construções do português europeu. A revisão continua necessária.

## Custos e serviços

O fluxo padrão usa ferramentas locais e pesquisa via yt-dlp. Não consome créditos do vidIQ, GPT Image ou uma API de texto. Não publica vídeos. Não exige assinatura nova nem administrador. Internet, armazenamento e energia continuam necessários.

O MCP do YouTube instalado anteriormente é uma integração separada. O painel não depende dele nem de uma chave do Google. O vidIQ também não é chamado automaticamente por este painel.

## Arquivos e operação

- Aplicativo: `C:\Users\Windows\edicao-ia\cortes-app`
- Lotes, arquivos, banco e registros: subpasta `data`
- Diagnóstico geral: `data\aplicativo.log`
- Diagnóstico de uma fonte: `data\<lote>\<vídeo>\diagnostico.log`
- Motor e projeto de referência: `C:\Users\Windows\cortes-trabalho\001-E07OTlhncP0`

Não mova a pasta do motor ou do ambiente `edicao-ia`: o aplicativo usa esses caminhos. Não remova fontes, vídeos ou caches antes de validar uma cópia no Drive e sua integridade. Nenhuma limpeza nem upload automático foi realizado nesta entrega.

Foram deixados dois lotes de validação, com quatro cortes aguardando sua revisão: um com o vídeo do piloto e outro com uma fonte escolhida pela pesquisa automática.

## Fontes dos componentes

[Argos Translate](https://github.com/argosopentech/argos-translate), [índice oficial de modelos](https://github.com/argosopentech/argospm-index), [CTranslate2](https://github.com/OpenNMT/CTranslate2), [Whisper](https://github.com/openai/whisper), [yt-dlp](https://github.com/yt-dlp/yt-dlp) e [FFmpeg](https://ffmpeg.org/).
