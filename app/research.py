"""Pesquisa pública e classificação rastreável, sem créditos de terceiros."""

from datetime import datetime, timezone
import json
import re
import time

from storage import observe

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

def canonical(text):
    text = re.sub(r"grand\s+theft\s+auto\s+(vi|6)\b", "gta 6", text, flags=re.I)
    text = re.sub(r"\bgta\s*(vi|6)\b", "gta 6", text, flags=re.I)
    text = re.sub(r"grand\s+theft\s+auto\s+(v|5)\b", "gta 5", text, flags=re.I)
    return re.sub(r"\bgta\s*(v|5)\b", "gta 5", text, flags=re.I).lower()


def normalize(entry):
    identifier = entry.get("id", "")
    if not VIDEO_ID.fullmatch(identifier):
        return None
    views = entry.get("view_count")
    timestamp = entry.get("timestamp")
    if not timestamp and entry.get("upload_date"):
        try:
            timestamp = datetime.strptime(entry["upload_date"], "%Y%m%d").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    observed = time.time()
    age_hours = max(1, (observed - timestamp) / 3600) if timestamp else None
    thumbnails = entry.get("thumbnails") or []
    return {"id": identifier, "url": f"https://www.youtube.com/watch?v={identifier}",
            "title": entry.get("title", identifier), "channel": entry.get("channel") or entry.get("uploader") or "Canal",
            "channel_id": entry.get("channel_id"), "views": views,
            "duration": entry.get("duration"), "published_at": timestamp,
            "observed_at": observed, "followers": entry.get("channel_follower_count"),
            "thumbnail": entry.get("thumbnail") or (thumbnails[-1]["url"] if thumbnails else None),
            "average_views_per_hour": round(views / age_hours, 2) if views is not None and age_hours else None,
            "measured_views_per_hour": observe(identifier, views, observed),
            "is_live": entry.get("is_live") or entry.get("live_status") == "is_live"}


def search(query, runner, directory, count=12, recent=False):
    prefix = 'ytsearchdate' if recent else 'ytsearch'
    command = ["yt-dlp", "--flat-playlist", "--dump-single-json",
               "--skip-download", "--no-warnings", f"{prefix}{count}:{query}"]
    data = json.loads(runner(command, directory, capture=True, timeout=180))
    return [item for entry in data.get("entries", []) if entry and (item := normalize(entry))]


def discover_page(options, runner, directory, notify, round_index, excluded):
    """Uma rodada durável; o controlador chama novas rodadas quando falta material."""
    topic = options['topic']
    if options.get('source_url'):
        if round_index:
            return [], [], {'query': 'link fornecido', 'sample_size': 0}
        item = hydrate({'url': options['source_url']}, runner, directory)
        if not item or item['is_live'] or not 12 <= (item['duration'] or 0) <= options['max_duration_minutes'] * 60:
            raise ValueError('A fonte está indisponível, ao vivo ou fora da duração permitida.')
        item.update(research_score=None, score_basis={'selection':'link fornecido'})
        chosen = [] if item['id'] in excluded else [item]
        query = 'link fornecido'
    else:
        variants = ['streamer reaction','reação trailer','melhores momentos','reaction gameplay',
                    'novidades gameplay','reaction highlights','stream highlights','análise detalhes',
                    'streamers reação','cortes gameplay','trailer react','ao vivo melhores momentos']
        query = topic + ' ' + variants[round_index % len(variants)]
        notify('research', 0, f'Pesquisa {round_index + 1}/{options["max_search_rounds"]}: {query}')
        sample = search(query, runner, directory, count=40, recent=round_index >= len(variants))
        terms = set(re.findall(r'\w+', canonical(topic))) - {'de','do','da','the','and','reacts','reaction','react','reação','reacoes'}
        version = re.search(r'\bgta\s+([56])\b',canonical(topic))
        def relevant(item):
            words = set(re.findall(r'\w+', canonical(item['title'])))
            if version and not {'gta',version[1]} <= words:
                return False
            return len(terms & words) >= max(1, (len(terms)+1)//2)
        eligible = [item for item in sample if item['id'] not in excluded and not item['is_live']
                    and 45 <= (item['duration'] or 0) <= options['max_duration_minutes'] * 60
                    and relevant(item)]
        chosen = rank(eligible, topic)
        # Interleave creators rather than exhausting one channel first.
        buckets = {}
        for item in chosen:
            buckets.setdefault(item.get('channel_id') or item['channel'], []).append(item)
        chosen = []
        while any(buckets.values()):
            for bucket in buckets.values():
                if bucket:
                    chosen.append(bucket.pop(0))
        for item in chosen:
            item.update(discovery_query=query, discovery_round=round_index+1)
    references = []
    if round_index == 0:
        try:
            refs = search(topic + ' reaction shorts', runner, directory, count=12)
            references = rank([item for item in refs if item.get('duration') and item['duration'] <= 180], topic)[:5]
        except (RuntimeError, ValueError, OSError):
            pass
    return chosen, references, {'query':query, 'new_candidates':len(chosen)}


def hydrate(video, runner, directory):
    raw = runner(["yt-dlp", "--no-playlist", "--skip-download", "--dump-single-json",
                  "--no-warnings", video["url"]], directory, capture=True, timeout=150)
    return normalize(json.loads(raw))


def rank(videos, topic):
    terms = set(re.findall(r"\w+", canonical(topic))) - {"de", "do", "the", "and", "reaction", "reação"}
    by_views = sorted(videos, key=lambda video: video.get("views") or 0)
    view_rank = {video["id"]: (index + 1) / len(by_views) for index, video in enumerate(by_views)}
    def velocity(video):
        measured = video.get("measured_views_per_hour")
        return measured if measured is not None else video.get("average_views_per_hour")
    rates = sorted([video for video in videos if velocity(video) is not None], key=velocity)
    rate_rank = {video["id"]: (index + 1) / len(rates) for index, video in enumerate(rates)}
    for video in videos:
        words = set(re.findall(r"\w+", canonical(video["title"])))
        relevance = len(terms & words) / max(1, len(terms))
        popularity = view_rank[video["id"]]
        rate = rate_rank.get(video["id"])
        score = .75 * popularity + .25 * relevance if rate is None else .45 * popularity + .3 * rate + .25 * relevance
        video["research_score"] = round(score * 100)
        video["score_basis"] = {"title_relevance": round(relevance, 3),
                                "views_percentile_in_sample": round(popularity, 3),
                                "average_rate_percentile_in_sample": round(rate, 3) if rate is not None else None,
                                "rate_kind": "medida entre observações" if video.get("measured_views_per_hour") is not None else "média desde a publicação",
                                "sample_size": len(videos)}
    return sorted(videos, key=lambda video: video["research_score"], reverse=True)


def discover(options, runner, directory, notify):
    topic = options["topic"]
    notify("research", 5, "Pesquisando vídeos e canais no YouTube")
    videos = search(topic + " streamer reaction", runner, directory)
    if not videos:
        raise RuntimeError("O YouTube não retornou vídeos. Tente outro termo ou retome o lote.")
    maximum = options["max_duration_minutes"] * 60
    eligible = [video for video in videos if not video["is_live"]
                and 45 <= (video["duration"] or 0) <= maximum]
    ranked = rank(eligible, topic)
    if options.get("source_url"):
        identifier = options["source_url"]
        probe = {"url": identifier}
        chosen = [hydrate(probe, runner, directory)]
        chosen[0]["research_score"] = None
        chosen[0]["score_basis"] = {"selection": "link fornecido"}
    else:
        detailed = []
        for candidate in ranked:
            if len(detailed) >= max(3, options["max_sources"]):
                break
            try:
                details = hydrate(candidate, runner, directory)
                if details and not details["is_live"] and (details["duration"] or 0) <= maximum:
                    detailed.append(details)
            except (RuntimeError, ValueError):
                continue
        chosen = rank(detailed, topic)[:options["max_sources"]]
        if not chosen:
            raise RuntimeError("Nenhum vídeo disponível se encaixou na duração escolhida.")
    notify("research", 12, "Buscando Shorts de referência e registrando as métricas")
    references = search(topic + " reaction shorts", runner, directory, count=10)
    references = rank([video for video in references if video.get("duration") and video["duration"] <= 180], topic)
    # Preserve three independent creators when the available sample supports it.
    independent = []
    channels = set()
    for reference in references:
        channel = reference.get("channel_id") or reference["channel"]
        if channel not in channels:
            independent.append(reference)
            channels.add(channel)
        if len(independent) == 5:
            break
    return chosen, independent, rank(videos, topic)
