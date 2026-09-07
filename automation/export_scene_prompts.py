"""Export reviewed scene fields verbatim; never infer scenes or write prose."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def keyed(items, label):
    result = {}
    for item in items:
        key = item['id']
        if key in result:
            raise ValueError(f'Duplicate {label}: {key}')
        result[key] = item
    return result


def validate(bundle, script_bytes, require_assets=False):
    if digest(script_bytes) != bundle['script_sha256']:
        raise ValueError('Source script hash changed; re-review affected scenes.')
    source = script_bytes.decode('utf-8')
    catalog = keyed(bundle['sentences'], 'sentence')
    scenes = keyed(bundle['scenes'], 'scene')
    shots = keyed(bundle['shots'], 'shot')
    frames = keyed(bundle['keyframes'], 'keyframe')
    if not all((catalog, scenes, shots, frames)):
        raise ValueError('Empty production input')
    owners = []
    for scene in scenes.values():
        if not scene['sentence_ids']:
            raise ValueError('Scene has no source evidence')
        owners.extend(scene['sentence_ids'])
        if scene.get('text_review_status') != 'REVIEWED_TEXT_ONLY':
            raise ValueError('Unreviewed scene fields')
    if owners != list(catalog):
        raise ValueError('Missing, repeated, reordered or unknown source sentence')
    for item in catalog.values():
        if source[item['source_start']:item['source_end']] != item['source_text']:
            raise ValueError('Sentence source span mismatch')
    used_frames = set()
    used_scenes = Counter()
    previous = None
    for shot in shots.values():
        if shot['scene_id'] not in scenes:
            raise ValueError('Unknown scene')
        used_scenes[shot['scene_id']] += 1
        for field in ('start_keyframe_id', 'end_keyframe_id'):
            if shot[field] not in frames:
                raise ValueError('Unknown keyframe')
            used_frames.add(shot[field])
        if shot['transition_in'] == 'CONTINUE':
            if previous is None or shot['start_keyframe_id'] != previous['end_keyframe_id']:
                raise ValueError('Continuation must share the exact planned keyframe ID')
        prompt = shot['video_prompt_en']
        if not isinstance(prompt, str) or not prompt.strip() or '\n' in prompt:
            raise ValueError('Video prompt must be one nonempty verbatim block')
        if shot['target_seconds'] <= 0:
            raise ValueError('Invalid planned duration')
        previous = shot
    if set(used_scenes) != set(scenes) or used_frames != set(frames):
        raise ValueError('Orphan scene or keyframe')
    for frame in frames.values():
        prompt = frame['prompt_en']
        if not isinstance(prompt, str) or not prompt.strip() or '\n' in prompt:
            raise ValueError('Image prompt must be one nonempty verbatim block')
        if require_assets:
            path = frame.get('asset_path')
            expected = frame.get('asset_sha256')
            if not path or not expected or not Path(path).is_file():
                raise ValueError('Real selected keyframe assets are not bound')
            if digest(Path(path).read_bytes()) != expected:
                raise ValueError('Selected keyframe asset hash changed')
    return frames


def export(bundle, script_bytes, destination, require_assets=False):
    frames = validate(bundle, script_bytes, require_assets)
    # Prevent unpublished source and prompts being written into the public clone.
    repo = Path(__file__).resolve().parents[1]
    destination = Path(destination).resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError('Private prompt output must be outside the public repository')
    shots = bundle['shots']
    first_use = []
    for shot in shots:
        for key in ('start_keyframe_id', 'end_keyframe_id'):
            if shot[key] not in first_use:
                first_use.append(shot[key])
    groups = {
        '04_Flow_images.md': [(k, frames[k]['prompt_en']) for k in first_use],
        '04_Flow_starts.md': [(s['id'], frames[s['start_keyframe_id']]['prompt_en']) for s in shots],
        '04_Flow_ends.md': [(s['id'], frames[s['end_keyframe_id']]['prompt_en']) for s in shots],
        '04_Omni_video_DRAFT.md': [(s['id'], s['video_prompt_en']) for s in shots],
    }
    payloads, index = {}, {}
    for filename, rows in groups.items():
        text = '\n\n'.join(prompt for _, prompt in rows) + '\n'
        payloads[filename] = text.encode('utf-8')
        offset, entries = 0, []
        for identity, prompt in rows:
            entries.append({'id': identity, 'start': offset, 'end': offset + len(prompt), 'prompt_sha256': digest(prompt.encode('utf-8'))})
            offset += len(prompt) + 2
        index[filename] = {'sha256': digest(payloads[filename]), 'offset_unit': 'Unicode code points', 'entries': entries}
    metadata = {
        'script_sha256': bundle['script_sha256'],
        'bundle_sha256': digest(json.dumps(bundle, ensure_ascii=False, sort_keys=True).encode('utf-8')),
        'status': 'ASSET_HASHES_CHECKED' if require_assets else 'PLANNED_TEXT_ONLY',
        'actual_generation_performed': False, 'files': index,
        'shots': [{k: s[k] for k in ('id', 'scene_id', 'start_keyframe_id', 'end_keyframe_id', 'transition_in', 'target_seconds')} for s in shots],
    }
    payloads['04_prompt_index.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    # Preflight all paths before writing anything. Repeated identical exports are safe.
    for filename, content in payloads.items():
        path = destination / filename
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f'Output changed; choose a new revision directory: {filename}')
    destination.mkdir(parents=True, exist_ok=True)
    for filename, content in payloads.items():
        (destination / filename).write_bytes(content)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('script', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--require-assets', action='store_true')
    args = parser.parse_args()
    result = export(json.loads(args.bundle.read_text(encoding='utf-8')), args.script.read_bytes(), args.destination, args.require_assets)
    print(json.dumps({'status': result['status'], 'files': list(result['files'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
