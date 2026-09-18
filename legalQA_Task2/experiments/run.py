"""Controlled LegalQA inference experiments; no training and no inferred split membership."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from model_production.pipeline import build_context_bundle
from legalqa_baseline.blocks import assemble_answer, split_answer


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def validate_config(config):
    for key in ('top_k', 'seed'):
        if type(config.get(key)) is not int or config[key] < (1 if key == 'top_k' else 0):
            raise ValueError(f'Invalid {key}')
    if config.get('limit') is not None and (type(config['limit']) is not int or config['limit'] < 1):
        raise ValueError('limit must be null or a positive integer')
    if not isinstance(config.get('score_threshold'), (float, int)) or not 0 <= config['score_threshold'] <= 1:
        raise ValueError('score_threshold must be between 0 and 1')
    variants = config.get('models')
    if not isinstance(variants, list) or not variants or len(set(variants)) != len(variants) or set(variants) - {'base', 'adapter'}:
        raise ValueError('models must be a nonempty unique list of base/adapter')


def assign_splits(rows, manifest):
    if manifest is None:
        return {str(r['id']): 'unverified' for r in rows}
    if not manifest.get('source'):
        raise ValueError('Split manifest must identify the original training export')
    train = set(map(str, manifest['train_ids']))
    heldout = set(map(str, manifest['heldout_ids']))
    if train & heldout:
        raise ValueError('Train/heldout IDs overlap')
    groups = {}
    result = {}
    for row in rows:
        qid = str(row['id'])
        group = 'train' if qid in train else 'heldout' if qid in heldout else 'unverified'
        normalized = ' '.join(row['question'].casefold().split())
        groups.setdefault(normalized, set()).add(group)
        result[qid] = group
    if any({'train', 'heldout'} <= labels for labels in groups.values()):
        raise ValueError('Duplicate normalized questions cross train/heldout')
    return result


def evidence_status(label, contexts):
    # ID coverage is a proxy, not proof that a truncated model prompt has evidence.
    gold = set(label.get('gold_unit_ids', []))
    if not gold:
        return None
    found = set()
    unknown = False
    for context in contexts:
        unknown |= not (context.get('covered_unit_ids') or context.get('unit_id'))
        found.update(context.get('covered_unit_ids', []))
        if context.get('unit_id'):
            found.add(context['unit_id'])
    if gold <= found:
        return True
    if unknown:
        return None
    return False


def mean_ci(values, seed):
    if not values:
        return {'n': 0, 'mean': None, 'ci95': None}
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(1000))
    return {'n': len(values), 'mean': statistics.fmean(values), 'ci95': [means[24], means[974]]}


def compare_runs(before, after, metric, seed):
    a = {r['id']: r[metric] for r in before}
    b = {r['id']: r[metric] for r in after}
    if a.keys() != b.keys() or len(a) != len(before) or len(b) != len(after):
        raise ValueError('Paired comparisons require identical unique question IDs')
    stats = mean_ci([b[q] - a[q] for q in sorted(a) if a[q] is not None and b[q] is not None], seed)
    return {'mean_delta': stats.pop('mean'), **stats}


def evaluate_rows(rows, generator, scorer, labels, top_k, seed, threshold):
    for row in rows:
        qid = str(row['id'])
        contexts = row['contexts'][:top_k]
        ref = row.get('reference_answer')
        result = {'id': qid, 'question': row['question'], 'contexts': contexts,
                  'oracle_source': row.get('oracle_source'),
                  'evidence_label_source': labels.get(qid, {}).get('source'),
                  'evidence_coverage_proxy': evidence_status(labels.get(qid, {}), contexts)}
        if contexts:
            bundle = build_context_bundle(row, top_k=top_k)
            qseed = (seed + int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16)) % (2**31)
            generated = generator.generate(row['question'], bundle['text'], bundle['citation_metadata'],
                                           seed=qseed, fewshot_examples=[])
            answer = assemble_answer(generated['lead'], bundle['text'], generated['conclusion'])
            result.update(status='completed', answer=answer, generation=generated, context=bundle)
        else:
            generated = {}
            result.update(status='empty_retrieval', answer='', generation={})
        scores = (scorer([result['answer']], [ref])['per_sample'][0] if contexts else
                  {'meteor': 0.0, 'rouge': 0.0}) if ref else None
        result.update(meteor=scores['meteor'] if scores else None,
                      rouge_l=scores['rouge'] if scores else None)
        result['answer_score_pass'] = result['meteor'] >= threshold if scores else None
        result['context_truncated'] = generated.get('context_truncated')
        # A numeric threshold only bins lexical scores; it is not a correctness label.
        coverage = result['evidence_coverage_proxy']
        if generated.get('context_truncated'):
            coverage = None
        result['bucket'] = (f"{'hit' if coverage else 'miss'}_"
                            f"{'high' if result['answer_score_pass'] else 'low'}") if coverage is not None and scores else 'unknown'
        result['generated_blocks'] = None
        if ref and generated:
            blocks = split_answer(ref)
            if blocks.confidence == 'high':
                result['generated_blocks'] = scorer(
                    [generated['lead'], generated['conclusion']], [blocks.lead, blocks.conclusion])['per_sample']
        yield result


def summarize(records, splits, seed):
    out = {'count': len(records), 'buckets': {}, 'splits': {}}
    for r in records:
        out['buckets'][r['bucket']] = out['buckets'].get(r['bucket'], 0) + 1
    for group in ('all', 'train', 'heldout', 'unverified'):
        selected = [r for r in records if group == 'all' or splits[r['id']] == group]
        out['splits'][group] = {m: mean_ci([r[m] for r in selected if r[m] is not None], seed)
                                for m in ('meteor', 'rouge_l')}
    out['generalization_gap'] = {}
    for metric in ('meteor', 'rouge_l'):
        a = out['splits']['train'][metric]['mean']
        b = out['splits']['heldout'][metric]['mean']
        out['generalization_gap'][metric] = a - b if a is not None and b is not None else None
    blocks = [r['generated_blocks'] for r in records if r['generated_blocks']]
    out['generated_blocks'] = {'n': len(blocks), **{
        name: {metric: mean_ci([b[i][metric] for b in blocks], seed)
               for metric in ('meteor', 'rouge')}
        for i, name in enumerate(('lead', 'conclusion'))}}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--adapter-path', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    config = read(args.config)
    validate_config(config)
    base = Path(args.config).resolve().parent
    resolve = lambda key: (base / config[key]).resolve()
    rows = read(resolve('packages'))
    if not rows or len({str(r['id']) for r in rows}) != len(rows):
        raise ValueError('Packages must be nonempty with unique IDs')
    for row in rows:
        if not isinstance(row.get('question'), str) or not row['question'].strip() or not isinstance(row.get('contexts'), list):
            raise ValueError('Invalid question/contexts')
        if row['contexts']:
            build_context_bundle(row, top_k=config['top_k'])
    split_manifest = read(resolve('split_manifest')) if config.get('split_manifest') else None
    splits = assign_splits(rows, split_manifest)
    # Validate all supplied rows before subsampling, so leakage cannot disappear by chance.
    rng = random.Random(config['seed'])
    rows = sorted(rows, key=lambda r: str(r['id']))
    if config.get('limit'):
        rows = rng.sample(rows, min(config['limit'], len(rows)))
    labels = read(resolve('labels')) if config.get('labels') else {}
    modes = {'retrieved': rows}
    missing = []
    if config.get('oracle_packages'):
        oracle_rows = read(resolve('oracle_packages'))
        oracle = {str(r['id']): r for r in oracle_rows}
        if len(oracle) != len(oracle_rows):
            raise ValueError('Duplicate oracle IDs')
        matched = []
        for row in rows:
            other = oracle.get(str(row['id']))
            if other:
                if other['question'] != row['question'] or other.get('reference_answer') != row.get('reference_answer'):
                    raise ValueError('Oracle/retrieval question or reference mismatch')
                if not other.get('oracle_source') or not other.get('contexts'):
                    raise ValueError('Oracle requires context and evidence provenance')
                build_context_bundle(other, top_k=config['top_k'])
                matched.append(other)
        if matched:
            modes['oracle'] = matched
        missing.append(f'oracle coverage: {len(matched)}/{len(rows)}')
    else:
        missing.append('oracle unavailable: provide evidence-backed oracle_packages')
    if not split_manifest:
        missing.append('train/heldout unavailable: no LLM training split manifest')
    if not labels:
        missing.append('retrieval hit/miss unavailable: no evidence labels')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'status': 'running', 'config': config, 'selected_ids': [str(r['id']) for r in rows],
                'started_at': datetime.now(timezone.utc).isoformat(),
                'splits': splits, 'missing': missing,
                'inputs_sha256': {key: hashlib.sha256(resolve(key).read_bytes()).hexdigest()
                                  for key in ('packages', 'oracle_packages', 'labels', 'split_manifest') if config.get(key)},
                'interpretation': 'Coverage is a pre-tokenization proxy; truncated contexts stay unknown in buckets. METEOR bins are not correctness labels. Gap is not memorization.'}
    write(output / 'manifest.json', manifest)
    started = time.monotonic()
    try:
        from legalqa_baseline.generation import QwenGenerator
        from legalqa_baseline.scoring import score_text_pairs
        production = read(ROOT / 'configs' / 'production.json')
        model = read(ROOT / 'configs' / 'models.json')[production['model_key']]
        manifest['generation_config'] = {'model': model, 'prompt_mode': production['prompt_mode'],
                                         'decoding_mode': 'greedy', 'enable_quality_retry': production['enable_quality_retry']}
        manifest['source_sha256'] = hashlib.sha256(b''.join(p.read_bytes() for p in
            [Path(__file__), *sorted((ROOT / 'src').rglob('*.py'))])).hexdigest()
        adapter_file = Path(args.adapter_path) / 'adapter_model.safetensors'
        if 'adapter' in config['models']:
            with adapter_file.open('rb') as stream:
                manifest['adapter_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        results = {}
        for variant in config['models']:
            if variant not in ('base', 'adapter'):
                raise ValueError('models must contain base and/or adapter')
            generator = QwenGenerator(model, adapter_path=args.adapter_path if variant == 'adapter' else None,
                                      prompt_mode=production['prompt_mode'], decoding_mode='greedy',
                                      enable_quality_retry=production['enable_quality_retry'])
            for mode, selected in modes.items():
                name = f'{variant}_{mode}'
                records = []
                with (output / f'{name}.jsonl').open('w', encoding='utf-8') as stream:
                    for record in evaluate_rows(selected, generator, score_text_pairs, labels, config['top_k'],
                                                config['seed'], config['score_threshold']):
                        stream.write(json.dumps(record, ensure_ascii=False) + '\n')
                        stream.flush()
                        records.append(record)
                        print(f'{name}: {len(records)}/{len(selected)} id={record["id"]}', flush=True)
                results[name] = records
                write(output / f'{name}_summary.json', summarize(records, splits, config['seed']))
                write(output / f'{name}_answers.json', {r['id']: {'answer': r['answer']} for r in records})
            del generator
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        comparisons = {}
        pairs = [('base_' + m, 'adapter_' + m) for m in modes]
        pairs += [(v + '_retrieved', v + '_oracle') for v in config['models']]
        for before, after in pairs:
            if before in results and after in results:
                ids = {r['id'] for r in results[after]}
                selected = [r for r in results[before] if r['id'] in ids]
                comparisons[f'{after}_minus_{before}'] = {m: compare_runs(selected, results[after], m, config['seed'])
                                                         for m in ('meteor', 'rouge_l')}
        write(output / 'comparisons.json', comparisons)
        manifest['status'] = 'completed'
    except Exception as exc:
        manifest.update(status='failed', error=repr(exc))
        raise
    finally:
        manifest['elapsed_seconds'] = round(time.monotonic() - started, 3)
        write(output / 'manifest.json', manifest)


if __name__ == '__main__':
    main()
