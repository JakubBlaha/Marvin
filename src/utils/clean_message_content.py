import re

import emoji

def clean_message_content(string: str) -> str:
    for i in re.finditer(r'<:\w+:\d+> ?', string):
        string = string.replace(i.group(0), '')

    string = emoji.demojize(string)

    return string.strip()

if __name__ == "__main__":
    print(clean_message_content('Test <:Test:1234> test'))