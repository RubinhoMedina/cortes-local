# Cortes Local — aplicação interna

Inicie por `iniciar.cmd` ou pelo atalho **Cortes Local** na área de trabalho. Para diagnóstico em primeiro plano: `C:\Users\Windows\edicao-ia\.venv\Scripts\python.exe -X utf8 app.py`.

Servidor Python padrão, exclusivamente em `127.0.0.1:3781`; frontend React compilado em `frontend/dist`; persistência SQLite em `data/cortes.db`; fila serial em `pipeline.py`. `research.py` consulta dados públicos via yt-dlp; `local_text.py` usa Argos EN–PT com CTranslate2 int8, duas threads, sem API externa. A redação dos metadados e a pontuação são heurísticas, não um modelo de previsão de alcance.

O motor original permanece em `C:\Users\Windows\cortes-trabalho\001-E07OTlhncP0`. Cada lote recebe sua cópia do executor, fluxo e enquadramento. O aplicativo reaproveita a transcrição e fontes do piloto quando aplicável. Os arquivos originais são preservados.

`reference_analysis.py` analisa o áudio dos primeiros 20 segundos de até três referências com Whisper base. Registra um trecho de até 22 palavras e o padrão da abertura, sem análise visual. O resultado é reutilizado em `data/reference-cache`. A redação do hook prioriza uma fala própria que corresponda ao padrão predominante disponível, sem copiar a fala da referência. Falhas de referência não impedem a produção das fontes.

Recompile a interface com `npm.cmd run build` dentro de `frontend`. Dependências Python adicionais instaladas no ambiente existente: `ctranslate2==4.9.0` e `sentencepiece==0.2.3`. Modelo de tradução: pacote oficial Argos `translate-en_pt-1_9`, baixado de `https://argos-net.com/v1/translate-en_pt-1_9.argosmodel`. O pacote baixado foi mantido em `models/en-pt.argosmodel`.

O runtime llama.cpp e o modelo Qwen avaliados durante o desenvolvimento foram mantidos no disco, mas não são usados pelo fluxo final. Nenhuma remoção foi feita.

Não há publicação, integração de pagamento ou limpeza automática. Antes de qualquer limpeza futura, validar upload e integridade no Drive. Fontes em inglês e português são as suportadas nesta versão.
