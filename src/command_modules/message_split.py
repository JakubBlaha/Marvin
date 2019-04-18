FORMATTERS = ['```', '`', '*', '**', '_']


def split(s: str, chunk_size=2000):
    # Need to make the chunk smaller, so the formatters don't exceed the boundaries
    chunk_size -= 2 * len(max(FORMATTERS, key=len))

    # Split to chunks
    chunks = [s[i:i + chunk_size] for i in range(0, len(s), chunk_size)]

    # Process the formatters
    for index, chunk in enumerate(chunks):
        for fmt in sorted(FORMATTERS, reverse=True):
            if chunk.count(fmt) % 2:
                chunks[index] += fmt
                chunks[index + 1] = fmt + chunks[index + 1]
                break

        # TODO Special case for code formatting

    return chunks


if __name__ == "__main__":
    print(
        split(
            '**Hello world**, I am a newbie `programmer`!```I love python!```',
            10))
