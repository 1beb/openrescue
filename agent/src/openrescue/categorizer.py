from openrescue.config import CategoriesConfig


def _matches(keyword: str, searchable: str) -> bool:
    kw = keyword.lower()
    if kw in searchable:
        return True
    # Also match the domain name without the TLD (e.g. "youtube.com" matches "YouTube")
    if "." in kw:
        name_part = kw.rsplit(".", 1)[0]
        if name_part in searchable:
            return True
    return False


def categorize(app_name: str, window_title: str, categories: CategoriesConfig) -> str:
    searchable = f"{app_name} {window_title}".lower()

    for keyword in categories.very_productive:
        if _matches(keyword, searchable):
            return "very_productive"

    for keyword in categories.productive:
        if _matches(keyword, searchable):
            return "productive"

    for keyword in categories.distracting:
        if _matches(keyword, searchable):
            return "distracting"

    for keyword in categories.very_distracting:
        if _matches(keyword, searchable):
            return "very_distracting"

    return "uncategorized"
