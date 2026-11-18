"""Pure-Python title reconciliation; deliberately CPU-bound for process comparisons."""
import re
import time
import unicodedata

PLATFORMS = {'pc','windows','playstation','ps4','ps5','xbox','switch','nintendo'}
EDITION_WORDS = {'goty','deluxe','definitive','remastered','remaster','ultimate','complete','bundle','collection','edition'}
ROMAN = {'ii':'2','iii':'3','iv':'4','v':'5','vi':'6','vii':'7','viii':'8','ix':'9','x':'10'}


def normalized(title):
    title = (title or '').replace('™', '').replace('®', '').replace('©', '')
    title = title.replace("'", '').replace('’', '').replace('＊', '').replace('&', ' and ')
    title = unicodedata.normalize('NFKD', title or '').casefold()
    title = ''.join(ch for ch in title if not unicodedata.combining(ch))
    words = re.findall(r'[a-z0-9]+', title)
    return ' '.join(ROMAN.get(word, word) for word in words if word not in PLATFORMS)


def edition_words(title):
    return EDITION_WORDS.intersection(normalized(title).split())


def base_title(title):
    return ' '.join(word for word in normalized(title).split() if word not in EDITION_WORDS)


def levenshtein(a, b):
    """Edit distance in Python, with only O(min(len(a), len(b))) memory."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for index, char_a in enumerate(a, 1):
        current = [index]
        for column, char_b in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def similarity(a, b):
    a, b = base_title(a), base_title(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    left, right = set(a.split()), set(b.split())
    tokens = len(left & right) / len(left | right)
    edit = 1 - levenshtein(a, b) / max(len(a), len(b))
    return .55 * tokens + .45 * edit


def match_game_candidates(game, candidates, threshold=.82, margin=.06):
    """Score every candidate; return a decision and the cost of the CPU stage."""
    started = time.perf_counter()
    titles = [game['name'], *(game.get('altTitles') or [])]
    ranked = []
    for candidate in candidates:
        title = candidate.get('title') or ''
        score = max(similarity(name, title) for name in titles)
        edition_conflict = any(edition_words(name) != edition_words(title)
                               and base_title(name) == base_title(title) for name in titles)
        ranked.append((score, edition_conflict, title, candidate))
    ranked.sort(key=lambda item: (-item[0], item[2].casefold()))
    best = ranked[0] if ranked else None
    def identity(item):
        appid = item[3].get('steamAppID')
        return ('steam', str(appid)) if appid else ('title', normalized(item[2]))
    second = next((item[0] for item in ranked[1:] if identity(item) != identity(best)), 0.0) if best else 0.0
    doubtful = bool(best and (best[1] or abs(best[0] - threshold) < margin or best[0] - second < margin))
    accepted = bool(best and best[0] >= threshold and not doubtful)
    finished = time.perf_counter()
    return {
        'gameId': game['steamAppId'],
        'accepted': best[3] if accepted else None,
        'candidate': best[3] if best else None,
        'score': round(best[0], 4) if best else 0.0,
        'doubtful': doubtful,
        'candidateCount': len(candidates),
        'matchSeconds': finished - started,
        'matchStarted': started,
        'matchFinished': finished,
    }
