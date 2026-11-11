# Lotes grandes — correção e validação

Corrigidos o envio da frase inteira como busca e o descarte da quantidade pedida. O plano interpreta o pedido original como tema **GTA 6**, meta **100**, até **50 fontes**, **20 candidatos por vídeo** e **12 rodadas**. Os limites ficam visíveis antes da execução e podem ser ajustados.

Implementados: pesquisa incremental com consultas diferentes, fila persistente, gravação a cada corte, deduplicação por origem/tempo/falas, repetição limitada, substituição de fontes com falha, pausa/retomada e retomada automática de lotes interrompidos ao abrir novamente o aplicativo. Resultados incompletos terminam com motivo explícito e opção de ampliar a pesquisa.

## Verificação

- Dez testes de controle passaram, incluindo a meta simulada de 100, primeira busca vazia, fonte com falha, limite exato da meta, repetição, pausa/retomada, ampliação do plano e recuperação no início do servidor.
- A frase que havia falhado foi usada em uma busca real: retornou 23 candidatos de fonte e cinco referências.
- Um teste real isolado produziu dois MP4. O servidor foi encerrado após o primeiro corte e reiniciado; retomou automaticamente, preservou o hash do primeiro vídeo e concluiu o segundo.
- Os dois vídeos foram decodificados integralmente, conferidos em 720 × 1280, e os pacotes ZIP passaram no teste de integridade.
- Pela interface, foram exercitados: pedido de 100 e prévia do plano, substituição da meta por um, início de um lote real, pausa e retomada. Esse lote terminou com um vídeo disponível para revisão.
- A retomada revelou um processo de edição órfão. O controle passou a usar Windows Job Objects por servidor/comando; o teste real de interrupção foi repetido e passou.
- O frontend de produção compilou; a interface foi conferida no navegador sem erros relevantes de console. O teste de segurança dos endpoints mantém origem/Host e cabeçalho obrigatório para alterações.
- A restauração do backup base aplicou também o código e a interface compilada da versão 2, sem substituir a aplicação original.

## Execução do usuário

O lote `5e9cf32437fa40c9`, que havia falhado, foi retomado com a meta de 100. O contador da ferramenta mostra a quantidade realmente produzida. **Os testes do controlador não significam que 100 vídeos reais já foram produzidos.**

A quantidade final depende de fontes acessíveis, momentos adequados e ausência de repetições. A pontuação continua heurística; contexto, tradução e enquadramento precisam de revisão humana. O YouTube pode exigir verificação ou limitar fontes. O programa preserva os resultados prontos e exibe a situação.

Não foram ativados serviços pagos, publicação, Git LFS, GitHub Actions ou limpeza. Os lotes anteriores foram preservados.
