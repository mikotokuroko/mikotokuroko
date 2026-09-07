"""Replace only activity regions using Metrics SVG metadata (standard library)."""

import argparse
import html
import json
from pathlib import Path
import re
import string
import sys
from urllib.parse import quote, urlsplit
import xml.etree.ElementTree as ET


def markdown(value):
    """Keep external text literal, including HTML and Markdown punctuation."""
    value = ' '.join(value.split())
    return ''.join(f'&#{ord(char)};' if char in string.punctuation else char
                   for char in value)


def artwork_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
            return None
        if any(ord(char) < 33 for char in value):
            return None
        return html.escape(value, quote=True)
    except ValueError:
        return None


def read_payload(path, source):
    try:
        root = ET.parse(path).getroot()
        nodes = [node for node in root.iter()
                 if node.tag.split('}')[-1] == 'metadata'
                 and node.get('id') == 'profile-data']
        if len(nodes) != 1:
            raise ValueError('expected one profile-data metadata element')
        data = json.loads(nodes[0].text or '')
        required = ('title', 'artist') if source == 'MUSIC' else ('title',)
        if not isinstance(data, dict) or not all(
            isinstance(data.get(key), str) and data[key].strip()
            for key in required
        ):
            raise ValueError('empty or incomplete payload')
        return data
    except (OSError, ET.ParseError, ValueError) as error:
        print(f'{source}: keeping previous content ({error})', file=sys.stderr)
        return None


def region_spans(text):
    spans = {}
    for source in ('MUSIC', 'STEAM'):
        start, end = f'<!-- {source}:START -->', f'<!-- {source}:END -->'
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f'{source}: missing or duplicated region marker')
        left, right = text.index(start) + len(start), text.index(end)
        if left > right:
            raise ValueError(f'{source}: reversed region markers')
        spans[source] = (left, right)
    music, steam = spans.values()
    if not (music[1] < steam[0] - len('<!-- STEAM:START -->')
            or steam[1] < music[0] - len('<!-- MUSIC:START -->')):
        raise ValueError('overlapping activity regions')
    return spans


def render(data, source, permanent_content):
    # Read the permanent destination by position, so editable link labels survive.
    match = re.search(r'\[[^\n]*?\]\((https?://[^\s)]+)\)', permanent_content)
    if not match:
        raise ValueError(f'{source}: missing permanent activity link')
    destination = quote(match[1], safe=':/?=&%+#@~;,-._')
    artwork = artwork_url(data.get('artwork' if source == 'MUSIC' else 'icon'))
    parts = []
    if artwork:
        width = 96 if source == 'MUSIC' else 120
        alt = html.escape(' '.join(data['title'].split()), quote=True)
        # Markdown owns the link; HTML is used only to size the artwork.
        parts.append(f'[<img src="{artwork}" width="{width}" alt="{alt}">]({destination})')
    parts.append(markdown(data['title']))
    if source == 'MUSIC':
        parts.append(markdown(data['artist']))
    return '\n\n' + '\n\n'.join(parts) + '\n\n'


def update(readme, music, steam):
    original = readme.read_bytes()
    text = original.decode('utf-8')
    spans = region_spans(text)  # Validate both regions before any write.
    replacements = []
    for source, path in (('MUSIC', music), ('STEAM', steam)):
        if path is None:
            continue
        data = read_payload(path, source)
        if data is not None:
            left, right = spans[source]
            after = text[right + len(f'<!-- {source}:END -->'):]
            # Only use the first paragraph following the generated region.
            permanent_content = after.strip().split('\n\n', 1)[0]
            replacements.append((left, right, render(data, source, permanent_content)))
    for left, right, content in sorted(replacements, reverse=True):
        text = text[:left] + content + text[right:]
    updated = text.encode('utf-8')
    if updated != original:
        readme.write_bytes(updated)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readme', type=Path, default=Path('README.md'))
    parser.add_argument('--music', type=Path)
    parser.add_argument('--steam', type=Path)
    args = parser.parse_args()
    try:
        changed = update(args.readme, args.music, args.steam)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print('Updated README.md' if changed else 'README.md unchanged')


if __name__ == '__main__':
    main()
