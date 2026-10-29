"""A versioned zero-step guard derived only from the frozen float64 recipe."""
import hashlib
import json
from pathlib import PurePosixPath

BASE_COMMIT='7dcaa48680daeac9a6025c09f9e4d138f5fcbda5'
BASE_FINGERPRINT='89efd6100f26c998148c7742b7900104618f02adfca0b535ae31baf5092d1e16'
BASE_FACETS_SHA='ae1965e82b705d63ee623dad0cd263785fe1ed6fd4c8871d9158b1c1e4785816'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def fingerprint(files):
    return sha(json.dumps({name:sha(raw) for name,raw in files.items()},sort_keys=True).encode())


def patch_facets(raw):
    if sha(raw)!=BASE_FACETS_SHA:raise ValueError('Renko correction requires the exact frozen float64 facets blob')
    for operator in ('+','-'):
        old=(f'            while c[t] {">=" if operator=="+" else "<="} last_brick {operator} box:\n'
             f'                last_brick {operator}= box\n').encode()
        guarded=(f'            while c[t] {">=" if operator=="+" else "<="} last_brick {operator} box:\n'
                 f'                if last_brick {operator} box == last_brick:\n'
                 '                    if np.isfinite(last_brick) and c[t] == last_brick:\n'
                 '                        break\n'
                 '                    raise FloatingPointError("Renko brick cannot advance for a nonzero price distance")\n'
                 f'                last_brick {operator}= box\n').encode()
        if raw.count(old)!=1:raise ValueError('frozen Renko loop layout differs')
        raw=raw.replace(old,guarded,1)
    return raw


def derive(files):
    if len(files)!=13 or fingerprint(files)!=BASE_FINGERPRINT:raise ValueError('Renko base thirteen-file recipe differs')
    if any(PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name for name in files):
        raise ValueError('unsafe Renko recipe path')
    result=dict(files);result['facets_world.py']=patch_facets(files['facets_world.py'])
    return result
