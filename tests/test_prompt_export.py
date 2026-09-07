import copy
import hashlib
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from export_scene_prompts import export, validate


class PromptExportTests(unittest.TestCase):
    def setUp(self):
        self.source = 'First. Second.'.encode('utf-8')
        self.bundle = {
            'script_sha256': hashlib.sha256(self.source).hexdigest(),
            'sentences': [
                {'id': 's1', 'source_start': 0, 'source_end': 6, 'source_text': 'First.'},
                {'id': 's2', 'source_start': 7, 'source_end': 14, 'source_text': 'Second.'},
            ],
            'scenes': [{'id': f'c{i}', 'sentence_ids': [f's{i}'], 'text_review_status': 'REVIEWED_TEXT_ONLY'} for i in (1, 2)],
            'keyframes': [{'id': f'k{i}', 'prompt_en': f'Exact prompt {i}.', 'asset_path': None, 'asset_sha256': None} for i in (1, 2, 3)],
            'shots': [
                {'id': 'v1', 'scene_id': 'c1', 'start_keyframe_id': 'k1', 'end_keyframe_id': 'k2', 'transition_in': 'CUT', 'video_prompt_en': 'First movement.', 'target_seconds': 10},
                {'id': 'v2', 'scene_id': 'c2', 'start_keyframe_id': 'k2', 'end_keyframe_id': 'k3', 'transition_in': 'CONTINUE', 'video_prompt_en': 'Second movement.', 'target_seconds': 10},
            ],
        }

    def test_exact_extraction_shared_frame_and_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            meta = export(self.bundle, self.source, temp)
            self.assertEqual('Exact prompt 1.\n\nExact prompt 2.\n\nExact prompt 3.\n', (Path(temp) / '04_Flow_images.md').read_text())
            for filename, data in meta['files'].items():
                text = (Path(temp) / filename).read_text()
                for row in data['entries']:
                    self.assertEqual(row['prompt_sha256'], hashlib.sha256(text[row['start']:row['end']].encode()).hexdigest())
            export(self.bundle, self.source, temp)

    def test_missing_sentence_and_false_continuation_rejected(self):
        bad = copy.deepcopy(self.bundle)
        bad['scenes'][1]['sentence_ids'] = ['s1']
        with self.assertRaises(ValueError):
            validate(bad, self.source)
        bad = copy.deepcopy(self.bundle)
        bad['shots'][1]['start_keyframe_id'] = 'k1'
        with self.assertRaises(ValueError):
            validate(bad, self.source)

    def test_changed_source_and_unbound_images_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.bundle, b'Changed source')
        with self.assertRaises(ValueError):
            validate(self.bundle, self.source, require_assets=True)

    def test_changed_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '04_Flow_images.md'
            path.write_text('User edit')
            with self.assertRaises(ValueError):
                export(self.bundle, self.source, temp)
            self.assertEqual('User edit', path.read_text())
            self.assertFalse((Path(temp) / '04_Flow_starts.md').exists())


if __name__ == '__main__':
    unittest.main()
