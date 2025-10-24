#!/usr/bin/env python
"""Attempt to convert a Transformers AutoModelForSpeechSeq2Seq checkpoint
into a Whisper-compatible checkpoint file.

Strategy:
- Load transformers model from provided local dir and get its state_dict.
- Load a reference Whisper model by name (e.g. 'large-v2') to obtain the
  expected architecture and dims.
- Map parameters from the transformers state dict into the whisper
  state dict using:
    1) exact name match
    2) suffix/prefix heuristics
    3) unique-shape heuristic (if only one unmatched parameter has that shape)
- Save checkpoint as a dict with keys 'dims' and 'model_state_dict' so
  whisper.load_model(path) can potentially load it.

This is a best-effort converter and will log mappings and any mismatches.
"""
from pathlib import Path
import argparse
import sys
import torch


def model_dir_for(name: str) -> Path:
    safe = name.replace('/', '_').replace(':', '_')
    return Path(__file__).resolve().parents[2] / 'models' / 'whisper' / safe


def serialize_dims(dims):
    # dims is a dataclass ModelDimensions; convert to dict
    try:
        return dims.__dict__
    except Exception:
        return dict(dims)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--local-dir', help='Local transformers model dir', required=True
    )
    parser.add_argument(
        '--whisper-ref',
        help='Whisper reference model name',
        default='large-v2',
    )
    args = parser.parse_args()

    local = Path(args.local_dir)
    if not local.exists():
        print('Local dir not found:', local)
        return 2

    print('Loading transformers model from', local)
    try:
        from transformers import AutoModelForSpeechSeq2Seq
    except Exception as e:
        print('transformers not available:', e)
        return 3

    tmodel = AutoModelForSpeechSeq2Seq.from_pretrained(str(local))
    t_state = {k: v.cpu() for k, v in tmodel.state_dict().items()}

    print('Loading reference whisper model:', args.whisper_ref)
    print('Loading reference to obtain target shapes')
    import whisper

    # Load reference whisper model (may download if needed)
    ref = whisper.load_model(args.whisper_ref, device='cpu')
    ref_state = {k: v.cpu() for k, v in ref.state_dict().items()}

    mapped = {}
    mapping_reasons = {}
    unmapped_ref = set(ref_state.keys())
    unmapped_t = set(t_state.keys())

    # 1) exact name matches
    for name in list(unmapped_ref):
        if name in t_state and ref_state[name].shape == t_state[name].shape:
            mapped[name] = t_state[name]
            mapping_reasons[name] = {'reason': 'exact_name'}
            unmapped_ref.remove(name)
            unmapped_t.remove(name)

    # 2) suffix-based heuristic: try to match by last N parts
    def parts(name):
        return name.split('.')

    for r in list(unmapped_ref):
        rparts = parts(r)
        found = None
        # prefer longer suffix matches
        for t in list(unmapped_t):
            tparts = parts(t)
            # try matching trailing 4 parts, then 3, then 2
            for n in (4, 3, 2):
                if (
                    len(rparts) >= n
                    and len(tparts) >= n
                    and rparts[-n:] == tparts[-n:]
                ):
                    if ref_state[r].shape == t_state[t].shape:
                        found = t
                        break
            if found:
                break
        if found:
            mapped[r] = t_state[found]
            mapping_reasons[r] = {'reason': 'suffix_match', 'mapped_to': found}
            unmapped_ref.remove(r)
            unmapped_t.remove(found)

    # 3) unique-shape heuristic
    shape_to_tnames = {}
    for t in unmapped_t:
        s = tuple(t_state[t].shape)
        shape_to_tnames.setdefault(s, []).append(t)

    for r in list(unmapped_ref):
        s = tuple(ref_state[r].shape)
        candidates = shape_to_tnames.get(s, [])
        if len(candidates) == 1:
            tname = candidates[0]
            mapped[r] = t_state[tname]
            mapping_reasons[r] = {'reason': 'unique_shape', 'mapped_to': tname}
            unmapped_ref.remove(r)
            unmapped_t.remove(tname)
            shape_to_tnames[s].remove(tname)

    # 4) prefix normalization heuristics - strip common wrappers like
    # 'model.' or 'base_model.' from transformers names and try matching
    # again by normalized names
    def normalize(name):
        for p in ('model.', 'base_model.', 'transformer.'):
            if name.startswith(p):
                return name[len(p):]
        return name

    norm_t_map = {normalize(t): t for t in unmapped_t}
    for r in list(unmapped_ref):
        nr = normalize(r)
        if nr in norm_t_map:
            t = norm_t_map[nr]
            if ref_state[r].shape == t_state[t].shape:
                mapped[r] = t_state[t]
                mapping_reasons[r] = {
                    'reason': 'normalized_name',
                    'mapped_to': t,
                }
                unmapped_ref.remove(r)
                unmapped_t.remove(t)

    # 5) alias and token-normalized suffix matching
    # Build a small alias map for common transformer->whisper token differences
    alias_tokens = {
        'q_proj': 'query',
        'k_proj': 'key',
        'v_proj': 'value',
        'out_proj': 'out',
        'fc1': 'mlp.0',
        'fc2': 'mlp.2',
        'layer_norm': 'ln',
        'layernorm': 'ln',
        'mlp_fc': 'mlp',
        'mlp_out': 'mlp.2',
        'embed_tokens': 'token_embedding',
    }

    def normalize_tokens(name):
        # split, replace aliases, and return token list
        toks = name.split('.')
        out = []
        for t in toks:
            out.append(alias_tokens.get(t, t))
        return out

    # try normalized suffix matches (4..2 tokens) using token aliasing
    # (norm_tokens_map not needed; we iterate directly over unmapped_t)
    for r in list(unmapped_ref):
        r_toks = normalize_tokens(r)
        found = None
        for t in list(unmapped_t):
            t_toks = normalize_tokens(t)
            for n in (4, 3, 2):
                if len(r_toks) >= n and len(t_toks) >= n:
                    if r_toks[-n:] == t_toks[-n:]:
                        if ref_state[r].shape == t_state[t].shape:
                            found = t
                            break
            if found:
                break
        if found:
            mapped[r] = t_state[found]
            mapping_reasons[r] = {
                'reason': 'token_normalized_suffix',
                'mapped_to': found,
            }
            unmapped_ref.remove(r)
            unmapped_t.remove(found)

    # 6) inverse-alias full-name substitution
    # For remaining unmapped refs, try to generate candidate transformer names
    # by substituting common whisper tokens with transformer variants (e.g.
    # query -> q_proj) and check for shape matches.
    inverse_alias = {
        'query': ['query', 'q_proj', 'q'],
        'key': ['key', 'k_proj', 'k'],
        'value': ['value', 'v_proj', 'v'],
        'out': ['out', 'out_proj', 'proj'],
        'mlp': ['mlp', 'fc1', 'fc2', 'dense'],
        'mlp0': ['mlp.0', 'fc1', 'dense0'],
        'mlp2': ['mlp.2', 'fc2', 'dense1'],
        'ln': ['ln', 'layer_norm', 'layernorm', 'layernorm1'],
        'token_embedding': [
            'token_embedding', 'embed_tokens', 'embeddings', 'token_embed'
        ],
    }

    from itertools import product

    def gen_candidates(rname):
        toks = rname.split('.')
        pools = []
        for tok in toks:
            # handle numbered mlp tokens like 'mlp', '0' -> 'mlp0'
            if tok.isdigit() and pools:
                # keep digits as their own token
                pools.append([tok])
                continue
                # attach digit to previous token key
                # signal by using e.g. 'mlp0'
                # we'll just keep digit as-is and handle in candidates
                pools.append([tok])
                continue
            low = tok
            if low in inverse_alias:
                pools.append(inverse_alias[low])
            else:
                pools.append([tok])
        # Limit combinatorial explosion
        max_comb = 256
        candidates = []
        for comb in product(*pools):
            cand = '.'.join(comb)
            candidates.append(cand)
            if len(candidates) >= max_comb:
                break
        return candidates

    for r in list(unmapped_ref):
        found = None
        candidates = gen_candidates(r)
        for cand in candidates:
            if cand in unmapped_t:
                if ref_state[r].shape == t_state[cand].shape:
                    found = cand
                    break
        if found:
            mapped[r] = t_state[found]
            mapping_reasons[r] = {
                'reason': 'inverse_alias',
                'mapped_to': found,
            }
            unmapped_ref.remove(r)
            unmapped_t.remove(found)

    # 6.5) deterministic substring substitution pass
    # Handle common differences in encoder/decoder block naming between
    # transformers checkpoint layouts and Whisper's reference names.
    # This creates candidate names by replacing well-known substrings
    # (e.g., 'encoder.blocks' -> 'encoder.layers') and checking shapes.
    substr_replacements = {
        'encoder.blocks': ['encoder.layers', 'encoder.layer', 'encoder.block'],
        'decoder.blocks': ['decoder.layers', 'decoder.layer', 'decoder.block'],
        'attention': ['self_attn', 'attn', 'attention'],
        'mlp.0': ['fc1', 'dense', 'feed_forward.w1'],
        'mlp.2': ['fc2', 'dense_output', 'feed_forward.w2'],
        'ln': ['layer_norm', 'layernorm', 'ln'],
        'token_embedding': ['embed_tokens', 'embeddings'],
        'encoder.positional_embedding': [
            'encoder.embed_positions',
            'encoder.pos_embedding',
        ],
    }

    def gen_subst_candidates(rname):
        # For each replacement key found in the name, build alternatives.
        parts = [rname]
        for key, reps in substr_replacements.items():
            new_parts = []
            for p in parts:
                if key in p:
                    for rep in reps:
                        new_parts.append(p.replace(key, rep))
                else:
                    new_parts.append(p)
            parts = new_parts
            # limit explosion early
            if len(parts) > 256:
                parts = parts[:256]
                break
        return parts

    for r in list(unmapped_ref):
        found = None
        candidates = gen_subst_candidates(r)
        for cand in candidates:
            if cand in unmapped_t:
                if ref_state[r].shape == t_state[cand].shape:
                    found = cand
                    break
        if found:
            mapped[r] = t_state[found]
            mapping_reasons[r] = {
                'reason': 'substr_replace',
                'mapped_to': found,
            }
            unmapped_ref.remove(r)
            unmapped_t.remove(found)

    # 6.75) canonicalize transformer names and match to ref names
    # Build a map of normalized transformer names -> original name
    # for the remaining transformer keys
    def normalize_transformer_name(tname):
        # strip leading model. or base_model.
        if tname.startswith('model.'):
            t = tname[len('model.'):]
        else:
            t = tname
        # common replacements to align with whisper ref naming
        subs = [
            ('layers.', 'blocks.'),
            ('self_attn.', 'attn.'),
            ('self_attn_layer_norm', 'attn_ln'),
            # transformers use 'encoder_attn_layer_norm' names for cross-attn
            # layer norms; normalize them to whisper's 'cross_attn_ln'
            ('encoder_attn_layer_norm', 'cross_attn_ln'),
            ('final_layer_norm', 'mlp_ln'),
            ('fc1.', 'mlp.0.'),
            ('fc2.', 'mlp.2.'),
            ('fc1', 'mlp.0'),
            ('fc2', 'mlp.2'),
            ('encoder_attn', 'cross_attn'),
            ('out_proj', 'out'),
            ('embed_positions', 'positional_embedding'),
            ('embed_tokens', 'token_embedding'),
            ('self_attn_layer_norm.weight', 'attn_ln.weight'),
            # map whisper 'ln_post' to transformer 'final_layer_norm'
            ('ln_post', 'final_layer_norm'),
        ]
        out = t
        for a, b in subs:
            out = out.replace(a, b)
        # remove repeated 'model.' if still present
        if out.startswith('model.'):
            out = out[len('model.'):]
        return out

    norm_map = {}
    for t in list(unmapped_t):
        nt = normalize_transformer_name(t)
        # store only first occurrence, but prefer exact shape matches later
        norm_map.setdefault(nt, []).append(t)

    for r in list(unmapped_ref):
        if r in norm_map:
            # try any candidate with same shape
            cand_list = norm_map[r]
            chosen = None
            for cand in cand_list:
                if ref_state[r].shape == t_state[cand].shape:
                    chosen = cand
                    break
            if chosen:
                mapped[r] = t_state[chosen]
                mapping_reasons[r] = {
                    'reason': 'transformer_canonicalized',
                    'mapped_to': chosen,
                }
                unmapped_ref.remove(r)
                unmapped_t.remove(chosen)

    # Final deterministic special-cases:
    # map encoder.ln_post -> model.encoder.final_layer_norm
    # Some transformer checkpoints use final_layer_norm naming for the
    # encoder post-norm; handle that here.
    for r in list(unmapped_ref):
        if r.startswith('encoder.ln_post.'):
            suffix = r.split('encoder.ln_post.')[1]
            candidate = f'model.encoder.final_layer_norm.{suffix}'
            if candidate in unmapped_t and (
                ref_state[r].shape == t_state[candidate].shape
            ):
                mapped[r] = t_state[candidate]
                mapping_reasons[r] = {
                    'reason': 'special_ln_post',
                    'mapped_to': candidate,
                }
                unmapped_ref.remove(r)
                unmapped_t.remove(candidate)

    # Log mapping summary
    print('Mapping summary:')
    print('  total ref params:', len(ref_state))
    print('  mapped params   :', len(mapped))
    print('  unmapped ref    :', len(unmapped_ref))

    if unmapped_ref:
        print('Sample unmapped reference params:')
        for i, n in enumerate(list(unmapped_ref)[:20]):
            print('   ', n, 'shape=', tuple(ref_state[n].shape))
        print('---')

    # Build final state dict: start from ref_state and replace mapped tensors
    final_state = {}
    for k, v in ref_state.items():
        if k in mapped:
            final_state[k] = mapped[k]
        else:
            final_state[k] = v

    dims = serialize_dims(ref.dims)

    out = local / 'model_converted.pt'
    print('Saving whisper-compatible checkpoint to', out)
    torch.save({'dims': dims, 'model_state_dict': final_state}, str(out))

    # Emit a mapping report for diagnostics (write before final silence)
    import json

    report = {
        'total_ref_params': len(ref_state),
        'mapped_params': len(mapped),
        'unmapped_ref': list(unmapped_ref),
        'mapping_reasons': mapping_reasons,
    }
    try:
        (local / 'mapping_report.json').write_text(
            json.dumps(report, indent=2)
        )
        print('Wrote mapping_report.json')
    except Exception as e:
        print('Failed to write mapping_report.json:', e)

    # also write a marker
    try:
        (local / 'whisper_converted_from_transformers.marker').write_text(
            'converted:true'
        )
    except Exception:
        pass

    print('Conversion done. You can try: whisper.load_model(str(out))')
    return 0


if __name__ == '__main__':
    sys.exit(main())
