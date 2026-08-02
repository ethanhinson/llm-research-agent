from thefuzz import fuzz

from agent.models import RawItem

SIMILARITY_THRESHOLD = 85


def cross_validate(items: list[RawItem]) -> list[RawItem]:
    groups: list[list[int]] = []

    for i, item in enumerate(items):
        placed = False
        for group in groups:
            representative = items[group[0]]
            if fuzz.ratio(item.title.lower(), representative.title.lower()) >= SIMILARITY_THRESHOLD:
                group.append(i)
                placed = True
                break
        if not placed:
            groups.append([i])

    for group in groups:
        if len(group) >= 2:
            for idx in group:
                items[idx].validated = True
                items[idx].sources_count = len(group)

    return items
