# Atualização da ferramenta — 12/11/2026

Esta revisão incorpora o planejamento incremental do lote, a interface atualizada e a opção experimental de usar um vídeo de reação fornecido pelo usuário.

## Arquivos atualizados
- app/app.py, app/batch.py, app/planning.py
- app/react_assets.py, app/REACT-FLOW.md
- app/frontend/src/main.jsx
- app/runtime-release.json

O código fonte da interface foi atualizado. Após restaurar o repositório, execute `npm.cmd ci` e `npm.cmd run build` em `app/frontend` para gerar a interface correspondente; o bundle pré-compilado anterior não representa esta revisão.

## Estado da validação
O teste local de cinco cortes concluiu cinco renderizações, mas a revisão visual identificou duplicação de cenas e texto excessivo. Esses cortes são protótipos para análise e não foram aprovados como formato final validado. A opção de reação é experimental e depende de um vídeo de reação fornecido localmente.

Dados de execução, vídeos, modelos, credenciais e chaves não fazem parte deste commit. Nenhum arquivo local foi removido.
