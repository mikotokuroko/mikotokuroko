"""Offline acceptance tests: python3 -m unittest discover -s scripts."""

import html
import json
from pathlib import Path
import tempfile
import unittest

from update_profile import update, region_spans

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.readme = self.folder / 'README.md'
        self.initial = (ROOT / 'README.md').read_text()
        self.readme.write_text(self.initial)

    def payload(self, source, data):
        path = self.folder / f'{source}.svg'
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg">'
                        '<metadata id="profile-data">'
                        + html.escape(json.dumps(data)) + '</metadata></svg>')
        return path

    def test_success_preservation_and_idempotence(self):
        music = self.payload('music', {'title': '夜 ' * 80, 'artist': '宇多田',
                                      'artwork': 'https://example.org/a?x=1&y=2'})
        steam = self.payload('steam', {'title': 'Stardew Valley',
                                      'icon': 'http://example.org/game.png'})
        self.assertTrue(update(self.readme, music, steam))
        result = self.readme.read_text()
        self.assertIn('width="96"', result)
        self.assertIn('width="120"', result)
        self.assertIn(('夜 ' * 80).strip(), result)
        self.assertIn('宇多田', result)
        def outside(text):
            for left, right in sorted(region_spans(text).values(), reverse=True):
                text = text[:left] + text[right:]
            return text
        self.assertEqual(outside(result), outside(self.initial))
        modified = self.readme.stat().st_mtime_ns
        self.assertFalse(update(self.readme, music, steam))
        self.assertEqual(modified, self.readme.stat().st_mtime_ns)

    def test_missing_and_unsafe_artwork(self):
        for art in [None, '', 'javascript:alert(1)', 'data:image/png;base64,a',
                    'file:///tmp/a', 'https://', 'https://[bad', 'https://a/\nx']:
            with self.subTest(art=art):
                music = self.payload('music', {'title': 'Song', 'artist': 'Artist',
                                              'artwork': art})
                update(self.readme, music, None)
                result = self.readme.read_text()
                left, right = region_spans(result)['MUSIC']
                self.assertNotIn('<img', result[left:right])
                self.assertIn('Song', result[left:right])

    def test_empty_and_failed_sources_preserve_previous(self):
        music = self.payload('music', {'title': 'Old song', 'artist': 'Artist'})
        steam = self.payload('steam', {'title': 'Old game'})
        update(self.readme, music, steam)
        for data in [None, {}, [], {'title': ''}, {'title': 1}]:
            music = self.payload('music', data)
            steam = self.payload('steam', {'title': 'New game'})
            update(self.readme, music, steam)
            self.assertIn('Old song', self.readme.read_text())
            self.assertIn('New game', self.readme.read_text())
        music.write_text('not XML')
        update(self.readme, music, self.folder / 'missing.svg')
        self.assertIn('Old song', self.readme.read_text())
        music = self.payload('music', {'title': 'New song', 'artist': 'Artist'})
        update(self.readme, music, self.folder / 'missing.svg')
        self.assertIn('New song', self.readme.read_text())
        self.assertIn('New game', self.readme.read_text())

    def test_external_text_is_literal(self):
        title = '*[夜](javascript:x) <script> & `code` ! # _ ~ |'
        music = self.payload('music', {'title': title, 'artist': '<b>"A"</b>',
                                      'artwork': 'https://example.org/"a"?x=1&y=2'})
        update(self.readme, music, None)
        result = self.readme.read_text()
        left, right = region_spans(result)['MUSIC']
        block = result[left:right]
        self.assertNotIn('<script>', block)
        self.assertIn('&lt;script&gt;', block)
        self.assertIn('&#42;&#91;夜&#93;', block)
        self.assertIn('&quot;a&quot;', block)
        self.assertEqual(html.unescape(block.strip().split('\n\n')[1]), title)

    def test_invalid_markers_never_write(self):
        music = self.payload('music', {'title': 'Song', 'artist': 'Artist'})
        for source in ('MUSIC', 'STEAM'):
            for edge in ('START', 'END'):
                marker = f'<!-- {source}:{edge} -->'
                for replacement in ('', marker + marker):
                    bad = self.initial.replace(marker, replacement)
                    self.readme.write_text(bad)
                    with self.assertRaises(ValueError):
                        update(self.readme, music, None)
                    self.assertEqual(self.readme.read_text(), bad)
        with self.assertRaises(ValueError):
            region_spans('<!-- MUSIC:START --><!-- STEAM:START -->'
                         '<!-- MUSIC:END --><!-- STEAM:END -->')

    def test_editable_captions_and_links(self):
        changed = self.initial.replace('Open my playlist', 'Listen here').replace(
            'https://embed.music.apple.com/mo/playlist/peaceful/pl.u-MDAWWjguWLNb69v?l=en',
            'https://music.apple.com/playlist/new')
        self.readme.write_text(changed)
        music = self.payload('music', {'title': 'Song', 'artist': 'Artist',
                                      'artwork': 'https://example.org/a'})
        update(self.readme, music, None)
        self.assertEqual(self.readme.read_text().count('https://music.apple.com/playlist/new'), 2)
        self.assertIn('[Listen here]', self.readme.read_text())


if __name__ == '__main__':
    unittest.main()
