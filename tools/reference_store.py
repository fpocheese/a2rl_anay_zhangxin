"""Lossless compact storage for original MATLAB graphics snapshots."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.io import loadmat


def pack(folder):
    folder = Path(folder)
    original = folder / 'matlab_reference.mat'
    results = loadmat(original, simplify_cells=True)['results']
    arrays = {}

    def encode(value):
        if isinstance(value, dict):
            return {k:encode(v) for k,v in value.items()}
        if isinstance(value, list):
            return [encode(v) for v in value]
        if isinstance(value, np.ndarray):
            key = hashlib.sha256(value.dtype.str.encode() + str(value.shape).encode()
                                 + value.tobytes()).hexdigest()
            arrays[key] = value
            return {'__array__':key}
        if isinstance(value, np.generic):
            return value.item()
        return value
    manifest = encode(results)
    np.savez_compressed(folder / 'matlab_arrays.npz', **arrays)
    (folder / 'matlab_snapshots.json').write_text(json.dumps(manifest, ensure_ascii=False))
    print('Packed unique arrays:', len(arrays))
    # Verify lossless round trip before dropping the temporary redundant MAT.
    restored = load(folder)
    assert len(restored) == len(results)
    assert json.dumps(encode(restored), ensure_ascii=False) == json.dumps(manifest, ensure_ascii=False)
    original.unlink()


def load(folder):
    folder = Path(folder)
    if not (folder / 'matlab_snapshots.json').exists():
        return loadmat(folder / 'matlab_reference.mat', simplify_cells=True)['results']
    with np.load(folder / 'matlab_arrays.npz', allow_pickle=False) as archive:
        arrays = dict(archive)
    def decode(value):
        if isinstance(value, dict):
            if '__array__' in value:
                return arrays[value['__array__']]
            return {k:decode(v) for k,v in value.items()}
        if isinstance(value, list):
            return [decode(v) for v in value]
        return value
    return decode(json.loads((folder / 'matlab_snapshots.json').read_text()))


if __name__ == '__main__':
    pack(Path(__file__).resolve().parents[1] / 'validation/generated')
