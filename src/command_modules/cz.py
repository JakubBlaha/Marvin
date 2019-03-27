CHARS: dict = {
    '2': 'ě',
    '3': 'š',
    '4': 'č',
    '5': 'ř',
    '6': 'ž',
    '7': 'ý',
    '8': 'á',
    '9': 'í',
    '0': 'é',
    ';': 'ů',
    'y': 'z',
    'z': 'y',
    '>': ':'
}
NO_TRIGGER: set = {'y', 'z'}

def fix_content(s: str) -> str:
    ignored_indexes = []
    ignoring = False
    for index, ch in enumerate(s):
        if ch == '<' and not ignoring:
            ignoring = True
        if ignoring:
            ignored_indexes.append(index)
        if ch == '>' and ignoring:
            ignoring = False

    # Check if required
    for ch in s:
        if ch in set(CHARS) - NO_TRIGGER:
            break
    else:
        return s

    for index, ch in enumerate(s):
        if index not in ignored_indexes:
            s = s[:index] + CHARS.get(s[index], s[index]) + s[index + 1:]

    return s
