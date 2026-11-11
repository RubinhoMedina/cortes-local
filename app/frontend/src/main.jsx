import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronDown,
  CircleHelp,
  Clapperboard,
  Copy,
  ExternalLink,
  Film,
  FolderOpen,
  Images,
  Layers3,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  Sparkles,
  Square,
  X,
} from "lucide-react";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "./style.css";

const api = async (path, body) => {
  const response = await fetch(
    path,
    body === undefined
      ? { signal: AbortSignal.timeout(20000) }
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Cortes-Local": "1",
          },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(20000),
        },
  ).catch(() => {
    throw new Error(
      "O processador local não respondeu. Verifique o atalho Cortes Local e tente novamente.",
    );
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || "Não foi possível concluir a ação");
  return data;
};
const number = (value) =>
  value == null
    ? "Não informado"
    : new Intl.NumberFormat("pt-BR", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value);
const duration = (seconds) =>
  `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
const date = (value) =>
  new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
const media = (job, path) =>
  `/media/${job.id}/${path.split("/").map(encodeURIComponent).join("/")}`;
const busy = (job) => ["queued", "processing"].includes(job.status);
const statusLabel = (job) =>
  ({
    ready: "Para revisar",
    processing: "Em andamento",
    queued: "Na fila",
    error: "Precisa de atenção",
    cancelled: "Cancelado",
    interrupted: "Interrompido",
    partial: "Meta parcial",
    paused: "Pausado",
  })[job.status] || job.status;

function App() {
  const [jobs, setJobs] = useState([]);
  const [system, setSystem] = useState(null);
  const [page, setPage] = useState("production");
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedClip, setSelectedClip] = useState(null);
  const [tab, setTab] = useState("publication");
  const [toast, setToast] = useState("");
  const [sending, setSending] = useState(false);
  const [filter, setFilter] = useState("all");
  const [options, setOptions] = useState({
    planner_version: 2,
    topic: "GTA 6",
    target_clips: "",
    max_sources: "",
    max_clips: 20,
    max_search_rounds: 12,
    max_duration_minutes: 30,
    whisper_model: "base",
    source_url: "",
    avoid_duplicates: true,
  });
  const [advanced, setAdvanced] = useState(false);
  const [draft, setDraft] = useState(null);
  const [plan, setPlan] = useState(null);
  const [planError, setPlanError] = useState("");
  const [formError, setFormError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [planningBusy, setPlanningBusy] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setPlanningBusy(true);
    const timer = setTimeout(async () => {
      try {
        const result = await api("/api/plan", options);
        if (!cancelled) {
          setPlan(result);
          setPlanError("");
        }
      } catch (error) {
        if (!cancelled) {
          setPlan(null);
          setPlanError(error.message);
        }
      } finally {
        if (!cancelled) setPlanningBusy(false);
      }
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [options]);

  const notify = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 4500);
  };
  const refresh = async () => {
    try {
      const [list, details] = await Promise.all([
        api("/api/jobs"),
        api("/api/system"),
      ]);
      setJobs(list);
      setSystem(details);
      setConnectionError("");
    } catch (error) {
      setConnectionError(
        "Não consegui falar com o processador local. Abra o atalho Cortes Local; esta página tentará reconectar.",
      );
    }
  };
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);
  const job = jobs.find((item) => item.id === selectedJob);
  const clip =
    job?.clips.find((item) => item.id === selectedClip) || job?.clips[0];
  useEffect(() => {
    if (
      job?.clips.length &&
      !job.clips.some((item) => item.id === selectedClip)
    ) {
      setSelectedClip(job.clips[0].id);
    }
  }, [selectedJob, job?.clips, selectedClip]);
  useEffect(() => {
    setDraft(clip ? structuredClone(clip) : null);
  }, [clip?.id, selectedJob]);
  const pending = jobs.reduce(
    (total, item) =>
      total + item.clips.filter((c) => c.status === "review").length,
    0,
  );
  const openJob = (item) => {
    setSelectedJob(item.id);
    setSelectedClip(item.clips[0]?.id || null);
    setPage("review");
  };
  const start = async (event) => {
    event.preventDefault();
    setSending(true);
    setFormError("");
    try {
      const created = await api("/api/jobs", options);
      setSelectedJob(created.id);
      setPage("review");
      await refresh();
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSending(false);
    }
  };
  const action = async (name) => {
    try {
      await api(`/api/jobs/${job.id}/${name}`, {});
      await refresh();
    } catch (error) {
      notify(error.message);
    }
  };
  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      notify("Copiado para a área de transferência");
    } catch {
      notify(
        "O navegador não permitiu copiar. Selecione o texto e use Ctrl+C.",
      );
    }
  };
  const save = async () => {
    try {
      await api(`/api/clips/${job.id}/${clip.id}/save`, {
        ...draft,
        tags: draft.tags,
      });
      await refresh();
      notify("Textos salvos");
    } catch (error) {
      notify(error.message);
    }
  };
  const review = async (status) => {
    try {
      await api(`/api/clips/${job.id}/${clip.id}/review`, { status });
      await refresh();
      notify(
        status === "approved"
          ? "Corte aprovado"
          : "Corte marcado para descarte",
      );
    } catch (error) {
      notify(error.message);
    }
  };
  const selectCover = async (index) => {
    try {
      await api(`/api/clips/${job.id}/${clip.id}/save`, {
        selected_cover: index,
      });
      setDraft({ ...draft, selected_cover: index });
      await refresh();
    } catch (error) {
      notify(error.message);
    }
  };
  const updateOption = (key, value) =>
    setOptions((previous) => ({ ...previous, [key]: value }));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            setPage("production");
            setSelectedJob(null);
          }}
        >
          <span className="brand-mark">
            <Clapperboard size={19} />
          </span>
          Cortes Local
        </a>
        <nav aria-label="Navegação principal">
          <button
            className={
              page === "production" && filter !== "review" ? "active" : ""
            }
            onClick={() => {
              setPage("production");
              setSelectedJob(null);
            }}
          >
            <Layers3 size={18} />
            Produção
          </button>
          <button
            className={
              page === "review" ||
              (page === "production" && filter === "review")
                ? "active"
                : ""
            }
            onClick={() => {
              setPage("production");
              setFilter("review");
              setSelectedJob(null);
            }}
          >
            <Film size={18} />
            Revisão{pending > 0 && <span className="nav-count">{pending}</span>}
          </button>
          <button
            className={page === "references" ? "active" : ""}
            onClick={() => setPage("references")}
          >
            <Search size={18} />
            Referências
          </button>
          <button
            className={page === "settings" ? "active" : ""}
            onClick={() => setPage("settings")}
          >
            <Settings2 size={18} />
            Configurações
          </button>
        </nav>
        <div className="sidebar-bottom">
          <span className="local-dot" />
          Processamento local<small>Arquivos neste computador</small>
        </div>
      </aside>
      <main>
        {connectionError && (
          <div className="persistent-error" role="alert">
            {connectionError}
          </div>
        )}
        <header className="topbar">
          <span>
            {page === "review" && job
              ? "Produção / Revisão"
              : page === "references"
                ? "Pesquisa / Referências"
                : page === "settings"
                  ? "Aplicativo / Configurações"
                  : "Biblioteca / Produção"}
          </span>
          <span className="topbar-local">
            <span className="local-dot" />
            Local
          </span>
        </header>

        {page === "production" && (
          <section className="content production">
            <div className="page-heading">
              <div>
                <h1>Produção de cortes</h1>
                <p>Do tema pesquisado aos vídeos prontos para revisar.</p>
              </div>
              <Clapperboard className="heading-icon" size={28} />
            </div>
            <form className="research-form" onSubmit={start}>
              <label htmlFor="topic">Qual é o tema ou pedido?</label>
              <div className="search-row">
                <Search size={21} />
                <input
                  id="topic"
                  value={options.topic}
                  onChange={(event) =>
                    updateOption("topic", event.target.value)
                  }
                  placeholder="Ex.: encontre vídeos de GTA 6 e me entregue 100 cortes"
                  minLength={2}
                  maxLength={600}
                  required
                />
                <button
                  className="primary"
                  disabled={sending || planningBusy || !!planError}
                >
                  {sending ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Play size={16} fill="currentColor" />
                  )}
                  Iniciar pesquisa
                </button>
              </div>
              <div className="plan-preview" aria-live="polite">
                {planningBusy ? (
                  <span>Interpretando o pedido…</span>
                ) : planError ? (
                  <p className="plan-error" role="alert">
                    {planError}
                  </p>
                ) : (
                  plan && (
                    <>
                      <strong>
                        Pesquisa: {plan.topic} · Meta: {plan.target_clips}{" "}
                        cortes
                      </strong>
                      <span>
                        Até {plan.max_sources} fontes · {plan.max_search_rounds}{" "}
                        rodadas de busca · candidatos escolhidos por conteúdo
                      </span>
                      <small>
                        A meta pode exigir horas de trabalho e várias fontes.
                        Cortes repetidos ou fracos não completam a quantidade.
                      </small>
                    </>
                  )
                )}
                {formError && (
                  <p className="plan-error" role="alert">
                    {formError}
                  </p>
                )}
              </div>
              <label className="target-control">
                Meta de cortes (opcional)
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={options.target_clips}
                  placeholder="Detectada no pedido; padrão 12"
                  onChange={(event) =>
                    updateOption("target_clips", event.target.value)
                  }
                />
                <small>
                  Preencha para substituir a quantidade escrita no pedido.
                </small>
              </label>
              <div className="research-footer">
                <span>YouTube · pesquisa e edição locais</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setAdvanced(!advanced)}
                  aria-expanded={advanced}
                >
                  Preferências do lote
                  <ChevronDown size={15} className={advanced ? "rotate" : ""} />
                </button>
              </div>
              {advanced && (
                <div className="preferences">
                  <label>
                    Limite de fontes para pesquisar
                    <select
                      value={options.max_sources}
                      onChange={(event) =>
                        updateOption(
                          "max_sources",
                          event.target.value ? Number(event.target.value) : "",
                        )
                      }
                    >
                      <option value="">Automático conforme a meta</option>
                      {[1, 3, 12, 25, 50, 100, 200].map((value) => (
                        <option key={value}>{value}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Teto de candidatos por vídeo
                    <select
                      value={options.max_clips}
                      onChange={(event) =>
                        updateOption("max_clips", Number(event.target.value))
                      }
                    >
                      {[2, 4, 10, 20, 50].map((value) => (
                        <option key={value}>{value}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Rodadas de pesquisa
                    <select
                      value={options.max_search_rounds}
                      onChange={(event) =>
                        updateOption(
                          "max_search_rounds",
                          Number(event.target.value),
                        )
                      }
                    >
                      {[4, 8, 12, 24, 40].map((value) => (
                        <option key={value}>{value}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={options.avoid_duplicates}
                      onChange={(event) =>
                        updateOption("avoid_duplicates", event.target.checked)
                      }
                    />
                    Evitar repetir cortes já produzidos
                  </label>
                  <label>
                    Duração máxima da fonte
                    <select
                      value={options.max_duration_minutes}
                      onChange={(event) =>
                        updateOption(
                          "max_duration_minutes",
                          Number(event.target.value),
                        )
                      }
                    >
                      {[10, 20, 30, 60, 120].map((value) => (
                        <option value={value} key={value}>
                          {value} minutos
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="source-url">
                    Ou use um vídeo específico
                    <input
                      type="url"
                      value={options.source_url}
                      onChange={(event) =>
                        updateOption("source_url", event.target.value)
                      }
                      placeholder="https://www.youtube.com/watch?v=…"
                    />
                  </label>
                  <p>
                    A quantidade final depende dos candidatos selecionados. A
                    transcrição local pode levar mais tempo em vídeos longos.
                  </p>
                </div>
              )}
            </form>
            <div className="section-heading">
              <h2>
                Seus lotes <span>{jobs.length}</span>
              </h2>
              <div className="filters">
                {[
                  ["all", "Todos"],
                  ["active", "Em andamento"],
                  ["review", "Para revisar"],
                ].map(([value, label]) => (
                  <button
                    className={filter === value ? "selected" : ""}
                    onClick={() => setFilter(value)}
                    key={value}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="job-list">
              {jobs
                .filter(
                  (item) =>
                    filter === "all" ||
                    (filter === "active"
                      ? busy(item)
                      : item.clips.some((c) => c.status === "review")),
                )
                .map((item) => (
                  <button
                    className="job-row"
                    key={item.id}
                    onClick={() => openJob(item)}
                  >
                    <div className="job-thumb">
                      {item.clips[0]?.covers?.[0] ? (
                        <img
                          src={media(item, item.clips[0].covers[0])}
                          alt="Prévia do lote"
                        />
                      ) : item.sources[0]?.thumbnail ? (
                        <img
                          src={item.sources[0].thumbnail}
                          alt="Vídeo selecionado"
                        />
                      ) : (
                        <Clapperboard size={25} />
                      )}
                    </div>
                    <div className="job-name">
                      <strong>{item.topic}</strong>
                      <span>
                        {date(item.created_at)}
                        {item.sources.length > 0 &&
                          ` · ${item.sources.length} vídeo${item.sources.length > 1 ? "s" : ""}`}
                      </span>
                    </div>
                    <span className={"job-status " + item.status}>
                      {busy(item) && (
                        <LoaderCircle size={14} className="spin" />
                      )}
                      {["ready", "partial"].includes(item.status) && (
                        <Check size={14} />
                      )}{" "}
                      {statusLabel(item)}
                    </span>
                    <span className="job-clips">
                      {item.clips.length
                        ? `${item.clips.length}/${item.options.target_clips || item.options.max_clips * item.options.max_sources} cortes`
                        : item.message}
                    </span>
                    <ArrowRight size={18} />
                  </button>
                ))}
              {!jobs.length && (
                <div className="empty">
                  <div className="empty-icon">
                    <Film size={28} />
                  </div>
                  <h3>Seu primeiro lote começa aqui</h3>
                  <p>
                    Pesquise um tema. Os vídeos concluídos aparecerão nesta
                    biblioteca.
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {page === "review" && job && (
          <section className="content review-page">
            <div className="review-heading">
              <button
                className="back-button"
                onClick={() => {
                  setPage("production");
                  setSelectedJob(null);
                }}
              >
                <ArrowLeft size={18} />
              </button>
              <div>
                <h1>{job.topic}</h1>
                <p>
                  {job.clips.length} cortes · {date(job.created_at)}
                </p>
              </div>
              <span className={"job-status " + job.status}>
                {statusLabel(job)}
              </span>
              <button className="secondary" onClick={() => action("open")}>
                <FolderOpen size={16} />
                Abrir pasta
              </button>
            </div>
            <div className="batch-stats">
              <strong>
                {job.clips.length}/
                {job.options.target_clips ||
                  job.options.max_clips * job.options.max_sources}{" "}
                cortes prontos
              </strong>
              <span>
                {job.stats?.sources_examined || 0} fontes examinadas ·{" "}
                {job.stats?.sources_failed || 0} falharam ·{" "}
                {job.stats?.duplicate_skips || 0} repetidos evitados
              </span>
              <span>
                {job.search_round || 0}/{job.options.max_search_rounds || 1}{" "}
                rodadas de pesquisa
              </span>
            </div>
            {busy(job) && (
              <div className="processing-panel">
                <div className="processing-title">
                  <LoaderCircle className="spin" size={20} />
                  <strong>{job.message}</strong>
                  <button
                    className="text-button"
                    onClick={() => action("pause")}
                  >
                    Pausar
                  </button>
                  <button
                    className="text-button"
                    onClick={() => action("cancel")}
                  >
                    <Square size={13} />
                    Cancelar lote
                  </button>
                </div>
                {job.active_operation && (
                  <p className="operation-time">
                    {job.active_operation.label} ·{" "}
                    {Math.max(
                      0,
                      Math.floor(
                        (Date.now() -
                          Date.parse(job.active_operation.started_at)) /
                          1000,
                      ),
                    )}{" "}
                    s nesta etapa
                  </p>
                )}
                <div className="progress">
                  <span style={{ width: `${job.progress}%` }} />
                </div>
                <div className="stage-labels">
                  {[
                    ["research", "Pesquisa"],
                    ["references", "Referências"],
                    ["transcript", "Transcrição"],
                    ["packaging", "Textos"],
                    ["render", "Edição"],
                    ["review", "Revisão"],
                  ].map(([value, label]) => (
                    <span
                      className={job.stage === value ? "current" : ""}
                      key={value}
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {[
              "error",
              "interrupted",
              "cancelled",
              "paused",
              "partial",
            ].includes(job.status) && (
              <div className="error-panel">
                <div>
                  <strong>
                    {job.status === "error"
                      ? "Este lote precisa de atenção"
                      : statusLabel(job)}
                  </strong>
                  <p>{job.error || job.message}</p>
                </div>
                {job.status !== "partial" && (
                  <button
                    className="secondary"
                    onClick={() => action("resume")}
                  >
                    <RefreshCw size={15} />
                    Retomar lote
                  </button>
                )}
                {["partial", "error"].includes(job.status) &&
                  !job.options.source_url && (
                    <button
                      className="secondary"
                      onClick={() => action("extend")}
                    >
                      Buscar mais fontes
                    </button>
                  )}
              </div>
            )}
            {job.warnings?.length > 0 && (
              <details className="warnings">
                <summary>
                  Observações do processamento ({job.warnings.length})
                </summary>
                {job.warnings.map((warning, index) => (
                  <p key={index}>{warning}</p>
                ))}
              </details>
            )}
            {clip && draft ? (
              <div className="review-grid">
                <div className="clip-list">
                  <div className="clip-list-label">CORTES DO LOTE</div>
                  {job.clips.map((item, index) => (
                    <button
                      key={item.id}
                      className={
                        "clip-item " + (clip.id === item.id ? "selected" : "")
                      }
                      onClick={() => setSelectedClip(item.id)}
                    >
                      <img
                        src={media(job, item.covers[item.selected_cover || 0])}
                        alt=""
                      />
                      <div>
                        <small>
                          Corte {String(index + 1).padStart(2, "0")} ·{" "}
                          {duration(item.duration)}
                        </small>
                        <strong>{item.title}</strong>
                        <span>
                          {item.status === "approved" ? (
                            <>
                              <CheckCheck size={12} />
                              Aprovado
                            </>
                          ) : item.status === "rejected" ? (
                            <>
                              <X size={12} />
                              Descartado
                            </>
                          ) : (
                            <>Editorial {item.score}/100</>
                          )}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
                <div className="player-column">
                  <div className="video-wrap">
                    <video
                      key={clip.id}
                      src={media(job, clip.media)}
                      poster={media(job, clip.covers[clip.selected_cover || 0])}
                      controls
                      playsInline
                      preload="metadata"
                    />
                  </div>
                  <div className="review-actions">
                    <button
                      className="approve"
                      onClick={() => review("approved")}
                    >
                      <Check size={17} />
                      Aprovar
                    </button>
                    <button
                      className="reject"
                      onClick={() => review("rejected")}
                    >
                      <X size={17} />
                      Descartar
                    </button>
                  </div>
                  <p className="source-credit">
                    {clip.source_channel}
                    <a href={clip.source_url} target="_blank" rel="noreferrer">
                      Ver fonte
                      <ExternalLink size={12} />
                    </a>
                  </p>
                </div>
                <div className="inspector">
                  <div className="inspector-tabs">
                    {[
                      ["publication", "Publicação"],
                      ["covers", "Capas"],
                      ["evidence", "Referências"],
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        className={tab === value ? "selected" : ""}
                        onClick={() => setTab(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {tab === "publication" && (
                    <div className="inspector-body">
                      <div className="editorial-score">
                        <div>
                          <Sparkles size={16} />
                          <strong>
                            {clip.score}
                            <small>/100</small>
                          </strong>
                          <span>Avaliação editorial</span>
                        </div>
                        <p>{clip.reason}</p>
                        {clip.reference_pattern && (
                          <p>
                            Padrão da abertura nas referências:{" "}
                            {clip.reference_pattern}.
                          </p>
                        )}
                      </div>
                      <Field label="Título" copy={() => copy(draft.title)}>
                        <textarea
                          aria-label="Título"
                          rows={2}
                          value={draft.title}
                          onChange={(event) =>
                            setDraft({ ...draft, title: event.target.value })
                          }
                        />
                      </Field>
                      <Field label="Hook" copy={() => copy(clip.hook)}>
                        <p className="hook-text">{clip.hook}</p>
                      </Field>
                      <Field
                        label="Descrição"
                        copy={() => copy(draft.description)}
                      >
                        <textarea
                          aria-label="Descrição"
                          rows={5}
                          value={draft.description}
                          onChange={(event) =>
                            setDraft({
                              ...draft,
                              description: event.target.value,
                            })
                          }
                        />
                      </Field>
                      <Field
                        label="Tags"
                        copy={() => copy(draft.tags.join(", "))}
                      >
                        <div className="tags">
                          {draft.tags.map((tag) => (
                            <span key={tag}>#{tag.replaceAll(" ", "")}</span>
                          ))}
                        </div>
                      </Field>
                      <div className="publication-actions">
                        <button className="secondary" onClick={save}>
                          Salvar textos
                        </button>
                        <a
                          className="primary"
                          href={`/api/bundle/${job.id}/${clip.id}`}
                        >
                          <ArrowDownToLine size={16} />
                          Baixar pacote
                        </a>
                      </div>
                      <p className="fine-print">
                        Inclui vídeo, capas, textos e referências. Revise as
                        falas e os fatos antes de publicar.
                      </p>
                    </div>
                  )}
                  {tab === "covers" && (
                    <div className="inspector-body">
                      <h3>Escolha uma capa</h3>
                      <p className="muted">
                        Quadros extraídos do próprio corte.
                      </p>
                      <div className="covers">
                        {clip.covers.map((cover, index) => (
                          <button
                            key={cover}
                            className={
                              (draft.selected_cover || 0) === index
                                ? "selected"
                                : ""
                            }
                            onClick={() => selectCover(index)}
                          >
                            <img
                              src={media(job, cover)}
                              alt={`Opção de capa ${index + 1}`}
                            />
                            {(draft.selected_cover || 0) === index && (
                              <span>
                                <Check size={14} />
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                      <a
                        className="secondary full"
                        href={media(
                          job,
                          clip.covers[draft.selected_cover || 0],
                        )}
                        download={`capa-${clip.id}.jpg`}
                      >
                        <ArrowDownToLine size={16} />
                        Baixar capa escolhida
                      </a>
                      <div className="cover-brief">
                        <div>
                          <Images size={17} />
                          <h3>Briefing para GPT Image</h3>
                        </div>
                        <p>{draft.cover_prompt}</p>
                        <button
                          className="secondary"
                          onClick={() => copy(draft.cover_prompt)}
                        >
                          <Copy size={14} />
                          Copiar briefing
                        </button>
                        <small>
                          A geração externa é opcional e pode ter custo no
                          serviço escolhido.
                        </small>
                      </div>
                    </div>
                  )}
                  {tab === "evidence" && (
                    <div className="inspector-body">
                      <h3>Dados da pesquisa</h3>
                      <p className="muted">
                        Dados públicos observados na pesquisa. A nota editorial
                        é uma avaliação por critérios das falas, sem garantia de
                        alcance.
                      </p>
                      <div className="source-evidence">
                        <small>VÍDEO DE ORIGEM</small>
                        <strong>{clip.source_title}</strong>
                        <span>{clip.source_channel}</span>
                        <a
                          href={clip.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Abrir no YouTube
                          <ExternalLink size={13} />
                        </a>
                      </div>
                      <h4>Shorts de referência</h4>
                      <References items={clip.references} compact />
                      <p className="fine-print">
                        A análise cobre a abertura falada, até 20 segundos.
                        Visualizações anteriores não garantem o desempenho deste
                        corte.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="empty processing-empty">
                <Film size={35} />
                <h3>
                  {busy(job)
                    ? "Seus cortes estão sendo preparados"
                    : "Os cortes aparecerão aqui"}
                </h3>
                <p>
                  {busy(job)
                    ? "Você pode fechar esta página. O processamento continua enquanto o computador estiver ligado."
                    : "Retome o lote para continuar a produção."}
                </p>
              </div>
            )}
          </section>
        )}

        {page === "references" && (
          <section className="content">
            <div className="page-heading">
              <div>
                <h1>Referências pesquisadas</h1>
                <p>
                  Vídeos observados nos seus lotes, com fonte e métricas
                  disponíveis.
                </p>
              </div>
            </div>
            {jobs.some((item) => item.references.length) ? (
              jobs
                .filter((item) => item.references.length)
                .map((item) => (
                  <section className="reference-section" key={item.id}>
                    <h2>
                      {item.topic}
                      <span>{date(item.created_at)}</span>
                    </h2>
                    <References items={item.references} />
                  </section>
                ))
            ) : (
              <div className="empty">
                <Search size={32} />
                <h3>A pesquisa constrói sua biblioteca</h3>
                <p>
                  Os Shorts usados como referência aparecerão aqui após o
                  primeiro lote.
                </p>
              </div>
            )}
          </section>
        )}

        {page === "settings" && (
          <section className="content settings-page">
            <div className="page-heading">
              <div>
                <h1>Configurações</h1>
                <p>Um fluxo local, com revisão antes da publicação.</p>
              </div>
            </div>
            <div className="settings-panel">
              <Setting
                label="Pesquisa de vídeos"
                value={system?.research_provider || "Carregando…"}
              />
              <Setting
                label="Geração de textos"
                value={
                  system?.local_model_ready
                    ? "Argos EN → PT · disponível neste computador"
                    : "Modelo local indisponível"
                }
              />
              <Setting label="Serviços pagos no fluxo" value="Desativados" />
              <Setting
                label="Processamento simultâneo"
                value="Um lote por vez"
              />
              <label className="model-setting">
                Qualidade da transcrição local
                <select
                  value={options.whisper_model}
                  onChange={(event) =>
                    updateOption("whisper_model", event.target.value)
                  }
                >
                  <option value="base">Base — prioriza velocidade</option>
                  <option value="large-v3-turbo">
                    Large Turbo — prioriza precisão
                  </option>
                </select>
                <small>
                  Usada quando as legendas públicas do YouTube não estão
                  disponíveis.
                </small>
              </label>
            </div>
            <div className="settings-note">
              <CircleHelp size={19} />
              <p>
                As notas de pesquisa comparam os vídeos encontrados na amostra.
                As notas dos cortes usam perguntas, repetições e reações nas
                falas. Nenhuma delas representa uma probabilidade de
                viralização.
              </p>
            </div>
          </section>
        )}
      </main>
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}

function Field({ label, copy, children }) {
  return (
    <div className="field">
      <div className="field-label">
        <label>{label}</label>
        <button
          onClick={copy}
          title={`Copiar ${label.toLowerCase()}`}
          aria-label={`Copiar ${label.toLowerCase()}`}
        >
          <Copy size={14} />
        </button>
      </div>
      {children}
    </div>
  );
}
function Setting({ label, value }) {
  return (
    <div className="setting">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function References({ items, compact = false }) {
  return (
    <div className={compact ? "reference-list compact" : "reference-list"}>
      {items.map((item) => (
        <a
          className="reference-item"
          href={item.url}
          key={item.id}
          target="_blank"
          rel="noreferrer"
        >
          {item.thumbnail ? (
            <img src={item.thumbnail} alt="" loading="lazy" />
          ) : (
            <div className="reference-placeholder">
              <Film size={20} />
            </div>
          )}
          <div>
            <strong>{item.title}</strong>
            <span>{item.channel}</span>
            <small>
              {number(item.views)} visualizações ·{" "}
              {duration(item.duration || 0)}
            </small>
            {item.opening_analysis && (
              <p className="opening-evidence">
                Abertura: {item.opening_analysis.pattern}
                {item.opening_analysis.excerpt_pt && (
                  <> · “{item.opening_analysis.excerpt_pt}”</>
                )}
              </p>
            )}
          </div>
          <ExternalLink size={14} />
        </a>
      ))}
      {!items.length && (
        <p className="muted">
          A pesquisa não retornou Shorts de referência suficientes para este
          lote.
        </p>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
