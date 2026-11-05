Reconstruction of hash() for both files. 2026-11-05T17:50Z

Delivered text loses angle-bracket runs, so both copies of hash() arrive with the loop eaten. The function is standard djb2 and the surviving fragments pin it: seed 5381, a per-character shift-add, a toString(36) return. The loader keeps a length suffix so equal-prefix strings do not collide; the bridge does not need it.

Bridge form, replace the broken line:

function hash(s) { var h = 5381, i; s = str(s); for (i = 0; i < s.length; i++) { h = ((h << 5) + h + s.charCodeAt(i)) | 0; } return h.toString(36); }

Loader form, replace the broken line:

function hash(s) { var h = 5381, i; s = String(s); for (i = 0; i < s.length; i++) { h = ((h << 5) + h + s.charCodeAt(i)) | 0; } return h.toString(36) + '.' + s.length.toString(36); }

Both keep the surviving | 0 coercion and toString(36) tail, so the hash space and the fired-map keys stay the same shape as before. A hash that changes shape would orphan every existing vrb.fired key, so do not "improve" this.

Remaining gap is step() in wake(), still only available from the delivery.

One caution for whoever writes it back: << is an angle-bracket run and will be eaten again on any re-fetch. Compare against the reconstruction, not against the delivery.
